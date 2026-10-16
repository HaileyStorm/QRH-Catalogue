#!/usr/bin/env python3
"""Reproducible QRH source catalogue. Python standard library only.

Sources remain authoritative; a build provides navigation, not proof validation.
"""
from __future__ import annotations

import argparse
import collections
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import quote, unquote

VERSION = 1
LIB = 'research/imports/qrtracker-20261013'
LOCAL_IDS = re.compile(r'(?<![A-Za-z0-9])(?:G\d{1,3}|T\d{2}[ab]?|A\d{2}|F\d{2}(?:\.[A-Za-z0-9]+)?|N2[789](?:\.[A-Za-z0-9]+)?)(?![A-Za-z0-9])')
LINK = re.compile(r'(?<!\\)\[(?:\\.|[^\]\\])*\]\(([^)]+)\)')
TOPICS = {
    'mobius': r'möbius|mobius|mertens|μ\(',
    'cubic': r'cubic|cube.row|cube.free',
    'sextic': r'sextic|sixth.power|sixth.order',
    'local-moment': r'local.moment|plain.moment|weighted.moment',
    'zero-free': r'zero.free|nonvanish',
    'height-uniformity': r'all.height|independent.height|height.uniform|bounded.height',
    'gaussian': r'gaussian|gauss sum|coprime.*field',
    'quaternion': r'quaternion|hurwitz',
    'source-foundation': r'positive.slot|source.ancestry|F0|stronger.weighted.source',
    'quartic': r'quartic|bernstein',
    'spectral': r'spectral|eigenvalue|sobolev|hecke',
    'approximation': r'hardy|residue.closure|approximation',
    'density': r'density|capacity|allowance',
}
METHODS = {
    'gram': r'gram|covariance|cross.norm',
    'mellin': r'mellin|log.scale',
    'projector': r'projector|projection|polar',
    'renewal': r'renewal|low.omega|inverse.column',
    'detector': r'detector|zero.signal|probe',
    'duality': r'dual|linear.program|minimax',
    'certificate': r'certificate|rational.evaluation|scalar.check',
    'completion': r'completion|common.mesh|commonmesh',
    'countermodel': r'countermodel|counterexample|refuted|obstruction',
}
OBJECTS = {
    'dirichlet-l': r'dirichlet|LFunction|L.function',
    'zeta': r'zeta|riemann',
    'hecke-family': r'hecke|ray.character|infinity.type',
    'physical-row': r'physical.row|completed.row|cube.row',
    'signed-energy': r'signed.*energy|signed.*norm|signed.*moment',
    'prime-slot': r'prime.slot|moving.prime|positive.slot',
    'cofactor': r'cofactor|low.omega|walsh',
    'source-contract': r'assumption|source.contract|source.premise|uniformity',
}


def compact(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8', newline='\n')


def slug(value):
    # Full UTF-8 digest prevents collisions from punctuation-normalized IDs.
    return re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')[:65] + '-' + digest(value.encode())[:10]


def markdown_text(value):
    text = str(value).replace('\n', ' ').replace('\r', '')
    return re.sub(r'([\\\[\]<>`|])', r'\\\1', text)


def record_files(directory, index):
    return [checked_file(directory, p) for p in index.get('record_files', ['records.jsonl'])]


def checked_file(directory, relative):
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('Data path escapes catalogue: '+str(relative))
    resolved = (directory/path).resolve()
    try:
        resolved.relative_to(directory.resolve())
    except ValueError:
        raise ValueError('Data symlink escapes catalogue: '+str(relative))
    return resolved


def records_digest(paths):
    h = hashlib.sha256()
    for path in paths:
        with path.open('rb') as f:
            for block in iter(lambda: f.read(1024*1024), b''):
                h.update(block)
    return h.hexdigest()


def status_labels(text):
    """Discovery labels inferred from source wording; never an acceptance verdict."""
    rules = {
        'conditional': r'conditional|CONDITIONAL',
        'open': r'\bOPEN\b|unproved|unfinished|remains? open|pending|not.proof.verified',
        'superseded': r'superseded|withdrawn|obsolete',
        'refuted': r'REFUTED|counterexample|false identity',
        'method-blocked': r'METHOD.BLOCKED',
        'dormant': r'dormant|revived|demoted|archive',
        'source-asserted-proved': r'\bPROVED\b',
        'unreviewed': r'unreviewed|not independently|text.indexed|raw.textual',
        'placeholder': r'sorry|placeholder',
    }
    return sorted(k for k, pattern in rules.items() if re.search(pattern, text, re.I))


class Builder:
    def __init__(self, repo, output, config):
        self.repo, self.output, self.config = repo, output, config
        self.records = {}
        self.inputs = {}
        self.edges = {}
        self.issues = []
        self.documents = {}
        self.local_components = {}
        self.file_cache = {}

    def read(self, relative, role='source'):
        relative = Path(relative).as_posix()
        if relative not in self.file_cache:
            path = self.repo / relative
            data = path.read_bytes()
            self.file_cache[relative] = data
            self.inputs[relative] = {'sha256': digest(data), 'bytes': len(data), 'roles': [role], 'groups': {}}
        elif role not in self.inputs[relative]['roles']:
            self.inputs[relative]['roles'].append(role)
        return self.file_cache[relative]

    def rows(self, relative, key=None):
        data = self.read(relative, 'inventory')
        if relative.endswith('.jsonl'):
            rows = [(json.loads(line), {'line': n}) for n, line in enumerate(data.decode('utf-8-sig').splitlines(), 1) if line.strip()]
            group = 'jsonl'
        else:
            root = json.loads(data.decode('utf-8-sig'))
            values = root[key] if key else root
            rows = [(r, {'json_pointer': '/' + (key + '/' if key else '') + str(i)}) for i, r in enumerate(values)]
            group = key or 'root'
        self.inputs[relative]['groups'][group] = {'expected': len(rows), 'represented': 0, 'record_ids': []}
        return rows, group

    def pointer(self, path, start=None, end=None, url=None, role='statement-proof'):
        p = {'path': path, 'role': role}
        if url:
            p['url'] = url
        if start is not None:
            p['line_start'] = int(start)
        if end is not None:
            p['line_end'] = int(end)
        if path and (self.repo / path).is_file():
            p['sha256'] = digest(self.read(path))
        elif path:
            self.issues.append({'kind': 'missing-source', 'path': path, 'role': role})
        return p

    def source_ref(self, inventory, location):
        return {'path': inventory, 'sha256': self.inputs[inventory]['sha256'], **location}

    def record(self, rid, title, kind, origin, raw=None, source=None):
        if rid in self.records:
            raise ValueError('Duplicate record ID: ' + rid)
        result = {
            'schema_version': VERSION, 'id': rid, 'aliases': [], 'identity_kind': 'source-occurrence',
            'semantic_component_id': None, 'title': title, 'kind': kind, 'origin': origin,
            'author': None, 'source_revision': None, 'statement': None, 'hypotheses': None,
            'quantifier_scope': None, 'quantitative_targets': None, 'quantitative_returns': None,
            'mathematical_status': 'unknown', 'review_status': 'unknown', 'formalization_status': 'unknown',
            'status_labels': [], 'conditional': False, 'source_relative': False,
            'topics': [], 'methods': [], 'objects': [], 'tags': [], 'unresolved_prerequisites': None,
            'pointers': [], 'relations': [], 'evidence': {}, 'raw_source_record': raw,
        }
        if source:
            result['source_record'] = source
            result['evidence']['default'] = {'basis': 'source-record', 'source': source, 'confidence': 'exact-transcription-or-pointer'}
        self.records[rid] = result
        return result

    def edge(self, source, target, kind, evidence, basis='source-navigation'):
        if source == target:
            return
        identity = compact([source, target, kind])
        edge = self.edges.setdefault(identity, {'source': source, 'target': target, 'kind': kind, 'basis': basis, 'evidence': []})
        if evidence not in edge['evidence']:
            edge['evidence'].append(evidence)

    def cover(self, inventory, group, rid):
        c = self.inputs[inventory]['groups'][group]
        c['represented'] += 1
        c['record_ids'].append(rid)

    def import_rows(self, inventory, key, origin, base, adapter):
        rows, group = self.rows(inventory, key)
        for raw, loc in rows:
            rid = raw.get('id') or raw.get('unit_id')
            if adapter == 'pr':
                rid = 'upstream:PR' + str(raw['number'])
            if adapter == 'claim':
                rid = 'cycle20-claim:' + raw['claim_id']
            if adapter == 'canonical':
                rid = 'cycle20-review:' + raw['id']
            if not rid:
                raise ValueError(f'No stable upstream ID in {inventory} {loc}')
            title = raw.get('title') or raw.get('name') or raw.get('module') or raw.get('label') or raw.get('claim') or rid
            kind = raw.get('kind') or ('module' if key == 'modules' else 'source-status-notice' if key == 'source_notices' else 'curated-family')
            if adapter in ('pr', 'claim', 'canonical'):
                kind = {'pr': 'pr-disposition', 'claim': 'reviewed-claim', 'canonical': 'result-review'}[adapter]
            r = self.record(rid, title, kind, origin, raw, self.source_ref(inventory, loc))
            r['aliases'] = [rid] if not rid.startswith(('upstream:', 'cycle20-')) else []
            prs = raw.get('prs') or ([raw['pr']] if raw.get('pr') else [])
            if adapter == 'pr':
                prs = [raw['number']]
            for occurrence in raw.get('occurrences', []):
                if occurrence.get('pr') not in prs:
                    prs.append(occurrence['pr'])
            r['origin'] = origin + ''.join(f'/PR{p}' for p in sorted(prs))
            r['tags'] += ['pr:' + str(p) for p in prs]
            r['statement'] = next((raw[k] for k in ('statement', 'statement_and_explicit_quantifiers', 'statement_excerpt', 'claim', 'audited_disposition', 'disposition') if raw.get(k)), None)
            r['hypotheses'] = next((raw[k] for k in ('assumptions', 'assumption_contract', 'assumption_context', 'full_relevant_assumptions_quantifiers', 'qualification') if raw.get(k)), None)
            r['quantifier_scope'] = next((raw[k] for k in ('full_assumptions_quantifiers', 'contract_scope', 'full_relevant_assumptions_quantifiers') if raw.get(k)), None)
            r['author'] = raw.get('author_credit') or raw.get('authorship')
            r['source_revision'] = raw.get('source_commit') or raw.get('source_head') or raw.get('head_sha')
            if raw.get('occurrences'):
                r['author'] = [o.get('author_credit') for o in raw['occurrences']]
                r['source_revision'] = [o.get('source_head') for o in raw['occurrences']]
            status = raw.get('status') or raw.get('verification_status') or raw.get('evidentiary_status') or raw.get('audited_disposition') or ''
            r['review_status'] = status or 'unknown'
            r['status_labels'] = status_labels(status)
            r['evidence']['status_labels'] = {'basis': 'inferred-source-wording', 'text': status}
            if adapter in ('claim', 'canonical'):
                r['mathematical_status'] = 'source-asserted: ' + status
                r['source_relative'] = True
            if adapter in ('text', 'liu', 'module', 'unit'):
                r['formalization_status'] = 'textual-source-retained; kernel replay unknown'
            r['unresolved_prerequisites'] = raw.get('remaining_analytic_obligations') or raw.get('scope_limitations')
            if raw.get('result') is not None:
                r['quantitative_returns'] = {'source_scalar_result': raw['result']}
            if adapter == 'maintenance':
                if raw.get('source'):
                    r['pointers'].append(self.pointer(base + '/' + raw['source'], raw.get('line')))
                else:
                    r['pointers'].append(self.pointer(base + '/report.md', role='review-context'))
            elif adapter == 'pr':
                r['pointers'].append(self.pointer(LIB + '/' + raw['report'], url=raw.get('url'), role='coverage-disposition'))
            elif adapter in ('canonical', 'claim'):
                r['pointers'].append(self.pointer('research/cycle20/' + raw.get('proof_location', raw.get('statement_quantifiers_and_proof', '')).split(' §')[0], role='proof-document'))
            elif adapter == 'closed':
                for entry in raw.get('source_pointers', []):
                    path, sep, anchor = entry.partition(':')
                    m = re.fullmatch(r'(\d+)(?:-(\d+))?', anchor)
                    p = self.pointer(base + '/originals/' + path, int(m[1]) if m else None, int(m[2] or m[1]) if m else None)
                    if anchor and not m:
                        p['selector'] = anchor
                    r['pointers'].append(p)
            elif adapter == 'liu':
                proof = raw.get('proof_pointer', {})
                r['pointers'].append({'url': proof.get('url'), 'line_start': proof.get('start_line'), 'line_end': proof.get('end_line'), 'sha256': raw.get('source_sha256'), 'role': 'reference-only-proof', 'license_handling': raw.get('license_handling')})
            elif adapter == 'curated':
                for p in raw.get('exact_source_pointers', []):
                    path = p.get('qrh_repository_relative') or (base + '/' + p['path'] if p.get('path') else None)
                    r['pointers'].append(self.pointer(path, role='curated-source'))
                if not r['pointers'] and raw.get('source_selector'):
                    selector = raw['source_selector'].split('#')[0]
                    path = selector if selector.startswith('research/') else base + '/' + selector
                    r['pointers'].append(self.pointer(path, role='curated-source'))
            elif adapter == 'text':
                proof = raw.get('proof_pointer', {})
                r['pointers'].append(self.pointer(base + '/' + proof['file'], proof.get('start_line'), proof.get('end_line')))
                for occurrence in raw.get('occurrences', []):
                    r['pointers'].append(self.pointer(base + '/' + occurrence['local'], proof.get('start_line'), proof.get('end_line'), role='retained-occurrence'))
            elif adapter == 'locator':
                r['pointers'].append(self.pointer(base + '/' + raw['file'], raw.get('line'), raw.get('end_line'), role='source-locator'))
            else:
                r['pointers'].append(self.pointer(base + '/' + raw['path'], raw.get('line_start'), raw.get('line_end'), raw.get('public_source_url')))
            if raw.get('module_id'):
                if raw['module_id'] not in self.records:
                    m = self.record(raw['module_id'], raw['module_id'], 'module', origin, source=r['source_record'])
                    m['pointers'] = r['pointers'][:]; m['review_status'] = 'explicit owning-module reference; module span not indexed separately'
                self.edge(raw['module_id'], rid, 'contains', r['source_record'], 'explicit-module-membership')
            if raw.get('parent_id'):
                self.edge(raw['parent_id'], rid, 'contains', r['source_record'], 'explicit-inventory-parent')
            r['conditional'] = 'conditional' in r['status_labels']
            self.cover(inventory, group, rid)

    def imports(self):
        packages = [
            ('local-moments/inventory.json', 'modules', 'upstream/local-moments', 'local-moments', 'module'),
            ('local-moments/inventory.json', 'units', 'upstream/local-moments', 'local-moments', 'unit'),
            ('local-moments/inventory.json', 'source_notices', 'upstream/local-moments', 'local-moments', 'notice'),
            ('historical/complete-textual-unit-inventory.jsonl', None, 'upstream/historical', 'historical', 'text'),
            ('historical/mathematical-locator-inventory.jsonl', None, 'upstream/historical', 'historical', 'locator'),
            ('historical/liu-mathematical-declarations.jsonl', None, 'upstream/historical', 'historical', 'liu'),
            ('historical/curated-mathematical-inventory.json', 'units', 'upstream/historical', 'historical', 'curated'),
            ('closed-prs/unit-inventory.json', 'units', 'upstream/closed-prs', 'closed-prs', 'closed'),
            ('maintenance/mathematical-exceptions.json', None, 'upstream/maintenance', 'maintenance', 'maintenance'),
            ('pr-coverage.json', 'prs', 'upstream/pr-dispositions', '', 'pr'),
        ]
        for path, key, origin, base, adapter in packages:
            self.import_rows(LIB + '/' + path, key, origin, LIB + ('/' + base if base else ''), adapter)
        for name, adapter in [('canonical_results', 'canonical'), ('expanded_claims', 'claim')]:
            self.import_rows('research/cycle20/checks/claim_registry.json', name, 'local/cycle20-review', 'research/cycle20', adapter)
        # Hash every collection's provenance/manifest, not just its index rows.
        for path in sorted((self.repo / LIB).rglob('*')):
            if path.is_file() and ('sources' not in path.parts and 'originals' not in path.parts and 'corpus' not in path.parts and 'evidence' not in path.parts):
                if path.suffix in ('.json', '.jsonl', '.md'):
                    self.read(path.relative_to(self.repo).as_posix(), 'provenance-support')

    def discover_local(self):
        seed = ['research/attempt-index.md', 'research/current-proof.md']
        seed += [p.relative_to(self.repo).as_posix() for p in sorted((self.repo / 'research/cycle20').glob('0[0-6]_*.md'))]
        seen, queue = set(), collections.deque(seed)
        while queue:
            path = queue.popleft()
            if path in seen:
                continue
            seen.add(path)
            body = self.read(path, 'local-navigation').decode('utf-8-sig')
            for link in LINK.findall(body):
                link = unquote(link.strip('<>').split('#')[0])
                if not link or '://' in link or link.startswith(('mailto:', '/')):
                    continue
                candidate = (self.repo / path).parent / link
                try:
                    rel = candidate.resolve().relative_to(self.repo).as_posix()
                except ValueError:
                    continue
                # Maintained attempt/proof stream, excluding creative prompts and frozen expert copies.
                eligible = re.match(r'research/(?:attempts/|cycle\d+/|review-cycle-\d+\.md)', rel)
                if eligible and candidate.is_file() and candidate.suffix == '.md' and not any(x in rel for x in ('export', 'snapshot', 'handoff/', 'written-proof/')):
                    queue.append(rel)
        return sorted(seen)

    def locals(self):
        paths = self.discover_local()
        for path in paths:
            lines = self.read(path).decode('utf-8-sig').splitlines()
            headers = []
            fenced = False
            for n, line in enumerate(lines, 1):
                if line.startswith('```'):
                    fenced = not fenced
                match = re.match(r'^(#{1,6})\s+(.+)', line) if not fenced else None
                if match:
                    headers.append((n, len(match[1]), match[2]))
            docid = 'local-document:' + path
            title = headers[0][2] if headers else Path(path).stem
            r = self.record(docid, title, 'source-document', 'local', source={'path': path, 'sha256': self.inputs[path]['sha256']})
            r['pointers'] = [self.pointer(path, 1, len(lines), role='document')]
            cyc = re.search(r'cycle(\d+)', path)
            if cyc:
                r['tags'].append('cycle:' + cyc[1])
                r['origin'] = 'local/cycle' + cyc[1]
            self.documents[path] = docid
            self.inputs[path]['groups']['document'] = {'expected': 1, 'represented': 1, 'record_ids': [docid]}
            self.inputs[path]['groups']['sections'] = {'expected': len(headers), 'represented': 0, 'record_ids': []}
            for i, (start, level, title) in enumerate(headers):
                end = next((h[0] - 1 for h in headers[i+1:] if h[1] <= level), len(lines))
                rid = 'local-section:' + digest((path + '\0' + title + '\0' + str(sum(1 for h in headers[:i] if h[2] == title))).encode())[:24]
                s = self.record(rid, title, 'research-section', r['origin'], source={'path': path, 'line_start': start, 'line_end': end, 'sha256': self.inputs[path]['sha256']})
                s['statement'] = '\n'.join(lines[start-1:end])
                s['pointers'] = [self.pointer(path, start, end)]
                s['tags'] += r['tags']
                s['status_labels'] = status_labels(title)
                s['evidence']['status_labels'] = {'basis': 'inferred-heading-wording', 'text': title}
                self.edge(docid, rid, 'contains', s['source_record'], 'source-section-structure')
                self.cover(path, 'sections', rid)
                # Only explicit leading IDs identify a result; body mentions are separate edges.
                lead = re.match(r'^(?:\d+(?:\.\d+)*\.?\s+)?(G\d{1,3}|T\d{2}[ab]?|A\d{2}|F\d{2}|N2[789])(?:[. :—-]|$)', title)
                if lead:
                    self.local_component(lead[1], title, s, 'family' if lead[1].startswith(('F', 'N')) else 'result')
                elif level == 1:
                    intro = '\n'.join(lines[start:min(start+14, end)])
                    explicit = re.search(r'(?:accepts?|integrates?)\s+(G\d{1,3})(?![\d-])', intro, re.I)
                    if explicit and not re.search(r'G\d{1,3}', title):
                        self.local_component(explicit[1].upper(), title + ' (' + explicit[1].upper() + ')', s, 'result')
            if path.endswith('04_HIERARCHICAL_IDEA_LEDGER.md'):
                self.inputs[path]['groups']['children'] = {'expected': 0, 'represented': 0, 'record_ids': []}
                for n, line in enumerate(lines, 1):
                    m = re.match(r'^- \*\*((?:F\d{2}|N2[789])\.[A-Za-z0-9]+)\s*[—–-]\s*(.*?)\*\*\s*(.*)', line)
                    if m:
                        rawid, clause, body = m.groups()
                        cid = 'local:' + rawid
                        child = self.record(cid, rawid + ' — ' + body.split('. ')[0], 'research-child', 'local/cycle20', {'id': rawid, 'status_clause': clause, 'exact_ledger_line': line}, {'path': path, 'line': n, 'sha256': self.inputs[path]['sha256']})
                        child['identity_kind'] = 'local-component'; child['semantic_component_id'] = cid
                        child['aliases'] = [rawid]; child['statement'] = line
                        child['pointers'] = [self.pointer(path, n, n)]
                        child['mathematical_status'] = 'source-asserted: ' + clause
                        child['status_labels'] = status_labels(clause)
                        child['conditional'] = 'conditional' in child['status_labels']
                        child['source_relative'] = True
                        child['tags'] += ['cycle:20']
                        self.local_components[rawid] = cid
                        self.edge('local:' + rawid.split('.')[0], cid, 'contains', child['source_record'], 'stable-ledger-family-child')
                        self.inputs[path]['groups']['children']['expected'] += 1
                        self.cover(path, 'children', cid)
        # Registry status remains evidence attached to the explicit stable T/A component.
        for rid, r in list(self.records.items()):
            if rid.startswith(('cycle20-review:', 'cycle20-claim:')):
                raw = r['raw_source_record']; target = self.local_components.get(raw.get('canonical_id', raw.get('id')))
                if target:
                    self.edge(rid, target, 'reviews', r['source_record'], 'explicit-reviewed-canonical-id')
                    self.records[target]['review_status'] = 'source-asserted Cycle20 audit; see linked reviews'
                    self.records[target]['source_relative'] = True
                    self.records[target]['evidence']['source_relative'] = {'basis': 'Cycle20-registry-explicit-scope', 'source': r['source_record'], 'scope': 'relative to explicitly identified inherited packages; no bulk baseline validation'}
        # Source links and known-ID mentions are navigable, never proved dependencies.
        for rid, r in list(self.records.items()):
            text = r.get('statement') or ''
            for rawid in sorted(set(LOCAL_IDS.findall(text))):
                target = self.local_components.get(rawid)
                if target:
                    self.edge(rid, target, 'mentions', r.get('source_record', {}), 'lexical-known-id-mention')
            for link in LINK.findall(text):
                src = r.get('source_record', {}).get('path', '')
                if not src.endswith('.md') or '://' in link:
                    continue
                candidate = (self.repo / src).parent / unquote(link.split('#')[0].strip('<>'))
                try:
                    rel = candidate.resolve().relative_to(self.repo).as_posix()
                except ValueError:
                    continue
                if rel in self.documents:
                    self.edge(rid, self.documents[rel], 'related', r['source_record'], 'explicit-markdown-link')

    def local_component(self, rawid, title, occurrence, kind):
        rid = 'local:' + rawid
        if rid not in self.records:
            r = self.record(rid, title, kind, occurrence['origin'], source=occurrence['source_record'])
            r['identity_kind'] = 'local-component'; r['semantic_component_id'] = rid
            r['aliases'] = [rawid]; r['pointers'] = occurrence['pointers'][:]
            r['statement'] = occurrence['statement']
            r['tags'] = occurrence['tags'][:]
            r['status_labels'] = occurrence['status_labels'][:]
            r['evidence']['identity'] = {'basis': 'explicit-leading-stable-local-id', 'source': occurrence['source_record']}
            self.local_components[rawid] = rid
        self.edge(rid, occurrence['id'], 'has_occurrence', occurrence['source_record'], 'same-explicit-local-id')
        occurrence['semantic_component_id'] = rid

    def link_upstream(self):
        for rid, r in list(self.records.items()):
            raw = r.get('raw_source_record') or {}
            for ptag in r['tags']:
                if ptag.startswith('pr:'):
                    self.edge('upstream:PR' + ptag[3:], rid, 'contains', r.get('source_record', {}), 'explicit-source-pr-membership')
            mapping = raw.get('local_library_mapping') or raw.get('library_mapping')
            paths = mapping.get('paths', []) if isinstance(mapping, dict) else []
            paths += raw.get('existing_library_matches', [])
            for path in paths:
                # The frozen inventories label these as analogues or partial matches.
                base = path.split(' §')[0].split(' ')[0]
                if base in self.documents:
                    self.edge(rid, self.documents[base], 'related', r.get('source_record', {}), 'source-library-navigation-not-equivalence')
            for path in raw.get('local_exact_source_matches', []) + raw.get('existing_exact_sources', []):
                if isinstance(path, dict):
                    path = path.get('path', '')
                if path in self.documents:
                    self.edge(rid, self.documents[path], 'exact_source_match', r.get('source_record', {}), 'inventory-explicit-exact-source-match')
        # Equal source bytes AND span only: preserve every indexed identity/occurrence.
        groups = collections.defaultdict(list)
        for rid, r in self.records.items():
            raw = r.get('raw_source_record') or {}
            if r['kind'] in ('pr-disposition', 'source-document', 'result-review', 'reviewed-claim', 'module'):
                continue
            for p in r['pointers']:
                if p.get('sha256') and p.get('line_start') is not None:
                    key = (p['sha256'], p['line_start'], p.get('line_end', p['line_start']))
                    groups[key].append(rid)
        for key, members in sorted(groups.items()):
            members = sorted(set(members))
            if len(members) < 2:
                continue
            groupid = 'exact-source:' + digest(compact(key).encode())[:24]
            g = self.record(groupid, 'Exact source span: ' + key[0][:12] + f' lines {key[1]}–{key[2]}', 'exact-source-group', 'source-identity')
            g['identity_kind'] = 'exact-source-group'; g['statement'] = 'Byte-identical file hash and equal recorded line span; mathematical equivalence and validity remain unestablished.'
            g['evidence']['identity'] = {'basis': 'sha256-and-equal-source-span', 'sha256': key[0], 'line_start': key[1], 'line_end': key[2]}
            g['pointers'] = self.records[members[0]]['pointers'][:1]
            for rid in members:
                self.edge(groupid, rid, 'exact_source_match', g['evidence']['identity'], 'byte-identity-not-theorem-equivalence')

    def overlays(self):
        path = self.config / 'components.jsonl'
        if path.exists():
            component_bytes = path.read_bytes()
            component_sha256 = digest(component_bytes)
            for n, line in enumerate(component_bytes.decode('utf-8').splitlines(), 1):
                if line.strip():
                    raw = json.loads(line); rid = raw['id']
                    if raw.get('illustrative_only'):
                        raise ValueError('Illustrative fixtures are not catalogue components: ' + rid)
                    r = self.record(rid, raw['title'], raw['kind'], raw.get('origin', 'curated'), raw, {'path': 'components.jsonl' if getattr(self, 'public', False) else 'research/catalogue/components.jsonl', 'line': n, 'sha256': component_sha256})
                    # Derived fields and overlays must not mutate the raw snapshot.
                    r.update(copy.deepcopy(raw))
        path = self.config / 'annotations.json'
        data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'records': {}, 'relations': []}
        for rid, fields in data.get('records', {}).items():
            if rid not in self.records:
                raise ValueError('Overlay unknown record: ' + rid)
            for field, annotation in fields.items():
                if field in ('id', 'raw_source_record', 'source_record', 'relations', 'identity_kind'):
                    raise ValueError('Overlay cannot overwrite identity/source field: ' + field)
                if not isinstance(annotation, dict) or 'value' not in annotation or not annotation.get('evidence'):
                    raise ValueError('Overlay field needs value and evidence: ' + rid + '/' + field)
                self.records[rid][field] = annotation['value']
                self.records[rid]['evidence'][field] = {'basis': 'maintained-overlay', **{k: v for k, v in annotation.items() if k != 'value'}}
        for edge in data.get('relations', []):
            if not edge.get('evidence'):
                raise ValueError('Overlay relation needs evidence')
            self.edge(edge['source'], edge['target'], edge['kind'], edge['evidence'], 'maintained-evidence-overlay')
            if edge['kind'] == 'supersedes':
                self.edge(edge['target'], edge['source'], 'superseded_by', edge['evidence'], 'inverse-evidenced-supersession')

    def enrich(self):
        correction = LIB + '/pr15-status-clarification.md'
        for r in self.records.values():
            text = r['title'] + '\n' + str(r['statement'] or '')
            source_pr = re.match(r'^pr(\d+):', r['id'])
            if source_pr:
                ptag = 'pr:'+source_pr[1]
                r['tags'].append(ptag)
                r['evidence']['source_pr'] = {'basis': 'explicit-upstream-inventory-id-namespace', 'id': r['id'], 'source_record': r.get('source_record'), 'qualification': 'Source membership only; no theorem validity or derivation use inferred.'}
                if '/PR' not in r['origin']:
                    r['origin'] += '/PR'+source_pr[1]
                if 'upstream:PR'+source_pr[1] in self.records:
                    self.edge(r['id'], 'upstream:PR'+source_pr[1], 'appears_in_submission', r['evidence']['source_pr'], 'explicit-inventory-pr-source-membership')
            for field, rules in [('topics', TOPICS), ('methods', METHODS), ('objects', OBJECTS)]:
                inferred = [key for key, pattern in rules.items() if re.search(pattern, text, re.I)]
                if field not in r['evidence']:
                    r[field] = sorted(set(r[field] + inferred))
                    r['evidence'][field] = {'basis': 'keyword-inferred-navigation-only', 'ruleset': 'catalogue.py-v1', 'confidence': 'uncalibrated'}
            if re.search(r'c11|\.1251459636|312864909', text, re.I):
                r['conditional'] = True; r['source_relative'] = True
                r['status_labels'] = sorted(set(r['status_labels'] + ['conditional', 'source-relative']))
                qualifier = {'basis': 'author-status-correction', 'qualification': 'c11 is a conditional source-relative benchmark; unfinished stronger weighted source and endpoint remain obligations.'}
                if getattr(self, 'public', False):
                    qualifier['source_record_id'] = 'pr15:withdrawn-completeness-claims'
                else:
                    qualifier['path'] = correction
                r['evidence']['endpoint_qualification'] = qualifier
                r['tags'].append('benchmark:c11')
            if r['conditional']:
                r['status_labels'] = sorted(set(r['status_labels'] + ['conditional']))
            if r['source_relative']:
                r['status_labels'] = sorted(set(r['status_labels'] + ['source-relative']))
            if 'conditional' in r['status_labels']:
                r['conditional'] = True
            r['tags'] = sorted(set(r['tags'] + ['topic:' + t for t in r['topics']] + ['method:' + t for t in r['methods']] + ['object:' + t for t in r['objects']]))
            raw = r.get('raw_source_record') or {}
            if r['kind'] in ('module', 'theorem', 'lemma', 'def', 'abbrev', 'instance', 'structure', 'formal-component') or r['kind'].startswith('formal_source_'):
                r.setdefault('formal_component', {
                    'component_kind': r['kind'].removeprefix('formal_source_'),
                    'repository': None, 'source_ref': r['source_revision'],
                    'path': next((p.get('path') for p in r['pointers'] if p.get('path')), raw.get('path')),
                    'module_name': raw.get('module') or raw.get('module_id'),
                    'fully_qualified_name': raw.get('fully_qualified_name'),
                    'source_declaration_name': raw.get('name'), 'namespace': None,
                    'lean_version': None, 'mathlib_version': None, 'toolchain': None,
                    'imports': raw.get('bundle_imports') or (raw.get('dependencies', {}).get('bundle_imports') if isinstance(raw.get('dependencies'), dict) else raw.get('dependencies')),
                    'external_packages': None, 'public_license': None,
                    'verification': {
                        'source_reported': {'status': r['review_status'], 'source_revision': r['source_revision'], 'evidence': r.get('source_record')},
                        'typechecked': {'status': 'unknown', 'source_revision': None, 'evidence': None},
                        'axioms_audited': {'status': 'unknown', 'source_revision': None, 'evidence': None},
                        'kernel_checked': {'status': 'unknown', 'source_revision': None, 'evidence': None},
                    }, 'qualification': 'Textual declaration/module only; source-reported verification is separate from independently evidenced checks.'})
        for edge in self.edges.values():
            if edge['source'] not in self.records or edge['target'] not in self.records:
                self.issues.append({'kind': 'unresolved-edge', **edge})
            else:
                self.records[edge['source']]['relations'].append({'target': edge['target'], 'kind': edge['kind'], 'basis': edge['basis'], 'evidence': edge['evidence']})
        for r in self.records.values():
            r['relations'].sort(key=lambda e: (e['kind'], e['target']))

    def build(self):
        self.imports(); self.locals(); self.link_upstream(); self.overlays(); self.enrich()
        return self.emit()

    def emit(self):
        self.output.mkdir(parents=True, exist_ok=True)
        entries = []
        offsets = {}
        record_path = self.output / 'records.jsonl'
        ids = sorted(self.records)
        with record_path.open('wb') as out:
            for pos, rid in enumerate(ids):
                r = self.records[rid]; line = (compact(r) + '\n').encode('utf-8')
                offsets[rid] = {'offset': out.tell(), 'bytes': len(line)}; out.write(line)
                text = '\n'.join(str(r.get(k) or '') for k in ('title', 'statement', 'hypotheses', 'quantifier_scope', 'review_status'))
                entries.append({k: r[k] for k in ('id', 'aliases', 'title', 'kind', 'origin', 'mathematical_status', 'review_status', 'formalization_status', 'status_labels', 'conditional', 'source_relative', 'tags', 'topics', 'methods', 'objects')} | {'search_text': text.casefold(), 'page': 'records/' + f'{pos//100+1:04d}.md' + '#' + slug(rid)})
        edges = sorted(self.edges.values(), key=lambda e: (e['source'], e['kind'], e['target']))
        write_json(self.output / 'index.json', {'schema_version': VERSION, 'entries': entries, 'offsets': offsets, 'edges': edges})
        self.browse(entries)
        receipt = {'schema_version': VERSION, 'builder': 'catalogue.py', 'evidence_class': 'local deterministic navigation build; no theorem validation', 'records': len(ids), 'edges': len(edges), 'inputs': dict(sorted(self.inputs.items())), 'issues': sorted(self.issues, key=compact), 'semantic_mapping': 'Partial/unknown mathematical overlaps remain distinct. Bare imports and mentions are not proof dependencies.', 'local_components': dict(sorted(self.local_components.items())), 'counts_by_kind': dict(sorted(collections.Counter(r['kind'] for r in self.records.values()).items())), 'records_sha256': digest(record_path.read_bytes())}
        write_json(self.output / 'coverage.json', receipt)
        return receipt

    def browse(self, entries):
        emitted_pages = set()
        pages = self.output / 'records'; pages.mkdir(exist_ok=True)
        lookup = {e['id']: e['page'] for e in entries}
        incoming_artifact_links = collections.defaultdict(list)
        for source, record in sorted(self.records.items()):
            for edge in record['relations']:
                if self.records[edge['target']].get('public_artifact'):
                    incoming_artifact_links[edge['target']].append({'source': source, **edge})
        facets = collections.defaultdict(lambda: collections.defaultdict(list))
        for e in entries:
            review_evidence = self.records[e['id']].get('evidence', {}).get('review_status') or {}
            review_group = ('unknown' if e['review_status']=='unknown' else
                'maintained-evidence-recorded' if isinstance(review_evidence, dict) and review_evidence.get('basis')=='maintained-evidence-overlay' else 'source-reported; inspect exact review status')
            values = {'kind': [e['kind']], 'origin': [e['origin'].split('/PR')[0]], 'status': e['status_labels'] or ['unknown'], 'review': [review_group], 'formalization': [e['formalization_status']], 'topic': e['topics'], 'method': e['methods'], 'object': e['objects'], 'pr': [t[3:] for t in e['tags'] if t.startswith('pr:')], 'cycle': [t[6:] for t in e['tags'] if t.startswith('cycle:')]}
            for facet, vals in values.items():
                for value in vals:
                    facets[facet][value].append(e)
        for start in range(0, len(entries), 100):
            number = start//100+1
            body = [f'# Records {number}', '', '[Catalogue directory](../DIRECTORY.md)', '']
            for e in entries[start:start+100]:
                r = self.records[e['id']]
                body += [f'<a id="{slug(e["id"])}"></a>', f'## {e["id"]}', '', markdown_text(r['title']), '', f'Kind: `{r["kind"]}` · Origin: `{r["origin"]}` · Mathematical status: {markdown_text(r["mathematical_status"])}', '', f'Review: {markdown_text(r["review_status"])} · Formalization: {markdown_text(r["formalization_status"])}', '', 'Navigation labels: ' + ', '.join(r['status_labels'] or ['unknown']) + (' · **CONDITIONAL SOURCE-RELATIVE**' if r['conditional'] and r['source_relative'] else ''), '']
                if r['tags']:
                    body += ['Tags (keyword tags are inferred; see JSON evidence): ' + ', '.join(r['tags']), '']
                for p in r['pointers']:
                    if getattr(self, 'public', False):
                        if p.get('url'):
                            label = p.get('source_label') or p.get('path') or p.get('role', 'source')
                            body += [f'- Public primary source: [{label}]({p["url"]})' + (' (archive member: `' + p['archive_member'] + '`)' if p.get('archive_member') else '')]
                        else:
                            body += [f'- Source not publicly available: `{p.get("path", p.get("source_label", "unknown"))}`; source text is not publicly accessible.']
                    elif p.get('path'):
                        # Install layout is always research/catalogue/generated/records/.
                        url = '../../../../../' + quote(p['path'], safe='/')
                        if p.get('line_start'):
                            url += '#L' + str(p['line_start'])
                        label = p['path'] + (':' + str(p['line_start']) if p.get('line_start') else '')
                        body += [f'- Source: [{label}]({url})']
                    elif p.get('url'):
                        body += [f'- Immutable source: [{p["role"]}]({p["url"]})']
                body += ['']
                if r.get('source_record'):
                    s = r['source_record']; label = s['path'] + (':' + str(s['line']) if s.get('line') else s.get('json_pointer', ''))
                    if getattr(self, 'public', False):
                        if s['path'] in ('components.jsonl', 'annotations.json'):
                            href = '../../'+s['path']+('#L'+str(s['line']) if s.get('line') else '')
                            body += [f'Public contribution evidence: [{label}]({href}); SHA-256 `{s.get("sha256", "unknown")}`.', '']
                        else:
                            body += [f'Frozen intake evidence: `{label}`; SHA-256 `{s.get("sha256", "unknown")}`; original source inventory not publicly available.', '']
                    else:
                        body += [f'Inventory/evidence: [{label}](../../../../../{quote(s["path"], safe="/")})', '']
                excerpt = str(r['statement'] or '')
                if excerpt:
                    body += ['````text', excerpt[:1100] + ('\n[Full statement/context: exact source or CLI show]' if len(excerpt)>1100 else ''), '````', '']
                relations = r['relations']
                if relations:
                    body += ['Linked records (direction retained; mentions/related are navigation):', '']
                    # Large containing records are navigable through facet lists and the CLI.
                    for edge in relations[:35]:
                        body += [f'- {edge["kind"]}: [{edge["target"]}]({Path(lookup[edge["target"]].split("#")[0]).name}#{lookup[edge["target"]].split("#")[1]})']
                    if len(relations)>35:
                        body += [f'- {len(relations)-35} further links: `traverse --id {r["id"]}`; full JSON retains every edge.']
                    body += ['']
                incoming = incoming_artifact_links.get(r['id'], [])
                if incoming:
                    body += ['Incoming recorded links (component → this public artifact; use class retained):', '']
                    for edge in incoming[:35]:
                        source_page = lookup[edge['source']]
                        body += [f'- {edge["kind"]}: [{edge["source"]}]({Path(source_page.split("#")[0]).name}#{source_page.split("#")[1]}) → this artifact']
                    if len(incoming)>35:
                        body += [f'- {len(incoming)-35} further incoming links: `traverse --id {r["id"]} --direction in`; full JSON retains every edge.']
                    body += ['']
            destination = pages / f'{number:04d}.md'
            destination.write_text('\n'.join(body)+'\n', encoding='utf-8', newline='\n')
            emitted_pages.add(destination)
        directory = ['# Unified QRH catalogue directory', '', '[Use and maintain the catalogue](../README.md) · [Coverage receipt](coverage.json)', '', '**Navigation is not proof acceptance. c11=.1251459636 is a conditional source-relative benchmark.**', '', f'{len(entries)} records. All retained inventories and local maintained proof/attempt sections share this directory.', '']
        browse = self.output / 'browse'; browse.mkdir(exist_ok=True)
        for facet, values in sorted(facets.items()):
            directory += ['## ' + facet, '']
            indexbody = ['# Browse by ' + facet, '', '[All facets](../DIRECTORY.md)', '']
            for value, members in sorted(values.items(), key=lambda item: item[0]):
                filename = facet + '-' + slug(value)
                chunks = (len(members)+249)//250
                indexbody += [f'- [{value} ({len(members)})]({filename}-01.md)']
                for n in range(chunks):
                    content = [f'# {facet}: {value}', '', '[Facet directory](' + facet + '.md) · [All facets](../DIRECTORY.md)', '', f'Page {n+1}/{chunks}; {len(members)} matching records.', '']
                    if n:
                        content += [f'[Previous]({filename}-{n:02d}.md)', '']
                    if n+1 < chunks:
                        content += [f'[Next]({filename}-{n+2:02d}.md)', '']
                    for e in members[n*250:(n+1)*250]:
                        content += [f'- [{e["id"]} — {markdown_text(e["title"])}](../{e["page"]})']
                    destination = browse / f'{filename}-{n+1:02d}.md'
                    destination.write_text('\n'.join(content)+'\n', encoding='utf-8', newline='\n')
                    emitted_pages.add(destination)
            destination = browse / (facet + '.md')
            destination.write_text('\n'.join(indexbody)+'\n', encoding='utf-8', newline='\n')
            emitted_pages.add(destination)
            directory += [f'[Browse {facet}](browse/{facet}.md)', '']
        directory += ['## Stable local families and results', '']
        for rawid, rid in sorted(self.local_components.items()):
            if '.' not in rawid:
                directory += [f'- [{rawid} — {markdown_text(self.records[rid]["title"])}]({lookup[rid]})']
        (self.output / 'DIRECTORY.md').write_text('\n'.join(directory)+'\n', encoding='utf-8', newline='\n')
        # Remove only obsolete files with this renderer's exact naming contract.
        # Otherwise a shrinking facet can retain stale private prose indefinitely.
        facet_names = 'kind|origin|status|review|formalization|topic|method|object|pr|cycle'
        for folder in (pages, browse):
            for path in folder.glob('*.md'):
                generated_name = (bool(re.fullmatch(r'\d{4,}\.md', path.name)) if folder == pages else
                    bool(re.fullmatch(r'(?:'+facet_names+r')(?:-[\w-]+-[0-9a-f]{10}-\d{2,})?\.md', path.name)))
                if generated_name and path not in emitted_pages:
                    if not path.resolve().is_relative_to(self.output.resolve()):
                        raise ValueError('Generated page escapes output: '+str(path))
                    path.unlink()


class Catalogue:
    def __init__(self, directory):
        self.directory = directory
        self.index = json.loads(checked_file(directory, 'index.json').read_text(encoding='utf-8'))
        self.allowed_files = set(self.index.get('record_files', ['records.jsonl']))
        self.by_id = {e['id']: e for e in self.index['entries']}
        self.aliases = collections.defaultdict(list)
        for e in self.index['entries']:
            for alias in e['aliases']:
                self.aliases[alias].append(e['id'])

    def resolve(self, rid):
        if rid in self.by_id:
            return rid
        candidates = self.aliases.get(rid, [])
        if len(candidates) != 1:
            raise ValueError('Unknown or ambiguous ID: ' + rid + '; candidates=' + str(candidates))
        return candidates[0]

    def record(self, rid):
        rid = self.resolve(rid); loc = self.index['offsets'][rid]
        filename = loc.get('file', 'records.jsonl')
        if filename not in self.allowed_files:
            raise ValueError('Offset references unlisted record shard:'+filename)
        with checked_file(self.directory, filename).open('rb') as f:
            f.seek(loc['offset']); return json.loads(f.read(loc['bytes']))

    def iter_records(self):
        for path in record_files(self.directory, self.index):
            with path.open(encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        yield json.loads(line)

    def query(self, args):
        result = []
        for e in self.index['entries']:
            if args.text and not all(t.casefold() in e['search_text'] for t in args.text):
                continue
            if args.kind and e['kind'] not in args.kind:
                continue
            if args.origin and not any(e['origin'].startswith(o) for o in args.origin):
                continue
            if args.status and not all(s in e['status_labels'] or s == e['mathematical_status'] for s in args.status):
                continue
            if any(getattr(args, field) and not all(v in e[key] for v in getattr(args, field)) for field, key in [('tag', 'tags'), ('topic', 'topics'), ('method', 'methods'), ('object', 'objects')]):
                continue
            if args.review and not all(v.casefold() in e['review_status'].casefold() for v in args.review):
                continue
            if args.formalization and not all(v.casefold() in e['formalization_status'].casefold() for v in args.formalization):
                continue
            if args.conditional and not e['conditional']:
                continue
            if args.source_relative and not e['source_relative']:
                continue
            result.append({k: v for k, v in e.items() if k != 'search_text'})
        return result

    def traverse(self, rid, kinds, direction, depth):
        rid = self.resolve(rid); visited = {rid}; queue = collections.deque([(rid, 0)]); collected = []
        adjacency = collections.defaultdict(list)
        for e in self.index['edges']:
            if kinds and e['kind'] not in kinds:
                continue
            if direction in ('out', 'both'):
                adjacency[e['source']].append((e['target'], e))
            if direction in ('in', 'both'):
                adjacency[e['target']].append((e['source'], e))
        seen_edges = set()
        while queue:
            current, level = queue.popleft()
            if level >= depth:
                continue
            for other, edge in adjacency[current]:
                identity = compact([edge['source'], edge['kind'], edge['target']])
                if identity not in seen_edges:
                    collected.append(edge); seen_edges.add(identity)
                if other not in visited:
                    visited.add(other); queue.append((other, level+1))
        return {'start': rid, 'direction': direction, 'depth': depth, 'record_ids': sorted(visited), 'edges': collected}


def validate(repo, directory):
    cat = Catalogue(directory); coverage = json.loads((directory / 'coverage.json').read_text(encoding='utf-8'))
    failures = []; records = {}; source_checks = {}; spans = 0
    for record_file in record_files(directory, cat.index):
      with record_file.open(encoding='utf-8') as f:
        actual_offset = 0
        for line in f:
            r = json.loads(line)
            loc = cat.index['offsets'].get(r.get('id'), {})
            size = len(line.encode('utf-8'))
            if loc.get('offset') != actual_offset or loc.get('bytes') != size or loc.get('file', 'records.jsonl') != record_file.relative_to(directory).as_posix():
                failures.append('offset/length mismatch:'+str(r.get('id')))
            actual_offset += size
            required = ('id', 'title', 'kind', 'origin', 'identity_kind', 'mathematical_status', 'review_status', 'formalization_status', 'conditional', 'source_relative', 'pointers', 'relations', 'evidence')
            for field in required:
                if field not in r:
                    failures.append('missing required field:'+r.get('id', '?')+'/'+field)
            for field in ('conditional', 'source_relative'):
                if not isinstance(r.get(field), bool):
                    failures.append('nonboolean field:'+r.get('id', '?')+'/'+field)
            if r.get('illustrative_only'):
                failures.append('illustrative fixture counted as catalogue record:'+r.get('id', '?'))
            if re.search(r'c11|\.1251459636|312864909', r.get('title','')+'\n'+str(r.get('statement') or ''), re.I) and not (r.get('conditional') and r.get('source_relative')):
                failures.append('c11 record lacks conditional source-relative qualification:'+r.get('id', '?'))
            formal = r.get('formal_component')
            if formal:
                for stage, claim in formal.get('verification', {}).items():
                    if stage != 'source_reported' and claim.get('status') not in (None, 'unknown', 'not-run'):
                        exact_ref = isinstance(formal.get('source_ref'), str) and bool(re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', formal['source_ref']))
                        if not exact_ref or not claim.get('evidence') or claim.get('source_revision') != formal.get('source_ref'):
                            failures.append('formal verification claim lacks exact revision/evidence:'+r.get('id', '?')+'/'+stage)
            if r['id'] in records:
                failures.append('duplicate ID:' + r['id'])
            records[r['id']] = r
            for p in r['pointers']:
                if p.get('path') and repo:
                    path = repo / p['path']
                    if not path.is_file():
                        failures.append('missing source:' + p['path']); continue
                    if p['path'] not in source_checks:
                        data = path.read_bytes(); source_checks[p['path']] = (digest(data), len(data.decode('utf-8-sig', errors='replace').splitlines()))
                    sha, count = source_checks[p['path']]
                    if p.get('sha256') and sha != p['sha256']:
                        failures.append('changed source:' + p['path'])
                    if p.get('line_start'):
                        spans += 1
                        # Frozen local-moments notes document one exclusive EOF marker.
                        if not 1 <= p['line_start'] <= count+1 or p.get('line_end', p['line_start']) < p['line_start'] or p.get('line_end', p['line_start']) > count+1:
                            failures.append('invalid span:' + r['id'] + ':' + p['path'])
                elif p.get('role') == 'reference-only-proof' and not p.get('url', '').startswith('https://'):
                    failures.append('invalid reference-only source:' + r['id'])
    for path, receipt in coverage['inputs'].items():
        if repo and digest((repo/path).read_bytes()) != receipt['sha256']:
            failures.append('input drift:' + path)
        for group, counts in receipt['groups'].items():
            if counts['expected'] != counts['represented']:
                failures.append('coverage mismatch:' + path + '/' + group)
            for rid in counts['record_ids']:
                if rid not in records:
                    failures.append('coverage missing record:' + rid)
    for edge in cat.index['edges']:
        if edge['source'] not in records or edge['target'] not in records:
            failures.append('dangling edge:' + compact(edge))
        if edge['kind'] in ('depends_on', 'equivalent', 'supersedes', 'superseded_by') and edge['basis'] != 'maintained-evidence-overlay' and not (edge['kind'] == 'superseded_by' and edge['basis'] == 'inverse-evidenced-supersession' and edge.get('evidence')):
            failures.append('unsupported semantic relation:' + compact(edge))
    if set(records) != set(cat.by_id):
        failures.append('search-index record coverage mismatch')
    if records_digest(record_files(directory, cat.index)) != coverage['records_sha256']:
        failures.append('record hash mismatch')
    anchor_cache = {}; resolved_cache = {}; existence_cache = {}
    for path in directory.rglob('*.md'):
        checked_file(directory, path.relative_to(directory))
        visible = re.sub(r'(?ms)^(`{3,})[^\n]*\n.*?^\1\s*$', '', path.read_text(encoding='utf-8'))
        for link in LINK.findall(visible):
            if '://' in link or link.startswith('#'):
                continue
            target, _, anchor = unquote(link).partition('#')
            if target.startswith('../../../../../') and repo:
                resolved = repo / target[len('../../../../../'):]
            else:
                resolved = path.parent / target
            normalized = Path(os.path.abspath(resolved))
            if normalized not in resolved_cache:
                resolved_cache[normalized] = normalized.resolve()
            resolved = resolved_cache[normalized]
            if not repo:
                try:
                    resolved.relative_to(directory.parent)
                except ValueError:
                    failures.append('browse link escapes catalogue checkout:' + link); continue
            if resolved not in existence_cache:
                existence_cache[resolved] = resolved.is_file()
            if not existence_cache[resolved]:
                failures.append('broken browse link:' + str(path.relative_to(directory)) + ' -> ' + link)
            elif anchor and not anchor.startswith('L'):
                if resolved not in anchor_cache:
                    anchor_cache[resolved] = set(re.findall(r'<a id="([^"]+)"></a>', resolved.read_text(encoding='utf-8')))
                if anchor not in anchor_cache[resolved]:
                    failures.append('missing browse anchor:' + link)
    return {'ok': not failures, 'records': len(records), 'edges': len(cat.index['edges']), 'source_files_checked': len(source_checks), 'source_spans_checked': spans, 'input_receipts_checked': len(coverage['inputs']), 'failures': sorted(set(failures)), 'mapping_issues': coverage['issues'], 'evidence_class': ('private source readback plus ' if repo else 'standalone committed data; external sources not fetched; ') + 'navigation coverage and integrity; not mathematical proof verification'}


PUBLIC_RAW_FIELDS = {
    'id', 'unit_id', 'claim_id', 'canonical_id', 'parent_id', 'module_id', 'kind',
    'name', 'title', 'module', 'label', 'pr', 'prs', 'statement',
    'statement_and_explicit_quantifiers', 'statement_excerpt', 'claim',
    'assumptions', 'assumption_contract', 'assumption_context',
    'full_relevant_assumptions_quantifiers', 'full_assumptions_quantifiers',
    'contract_scope', 'qualification', 'scope_limitations', 'status',
    'verification_status', 'evidentiary_status', 'dependency_status',
    'dependencies', 'validation_class', 'review_depth', 'result',
    'next_decisive_check', 'maps_to', 'local_match', 'local_relation',
    'novelty_status', 'semantic_deduplication', 'match_basis',
    'retention', 'preservation_disposition', 'development_usefulness',
    'prospective_use', 'author_credit', 'authorship', 'license_handling',
    'audited_disposition', 'source_sections', 'proof_location',
    'statement_quantifiers_and_proof', 'status_clause', 'exact_ledger_line',
    'introduced_commit', 'commit_utc', 'author_statement_date', 'limitation',
    'affected_contracts', 'disposition', 'head_sha', 'head_repo', 'state',
}


def public_safe(value):
    """Remove operational identifiers/absolute paths; preserve mathematical text."""
    if isinstance(value, dict):
        return {k: public_safe(v) for k, v in value.items() if k not in ('host_id', 'task_id', 'session_id', 'human_owner_id', 'workspace_instance_id', 'retrieved_utc')}
    if isinstance(value, list):
        return [public_safe(v) for v in value]
    if isinstance(value, str):
        value = re.sub(r'(?i)\b[A-Z]:[\\/](?:Users|Windows|Program Files|Documents)[\\/][^\s`\]"<>]+', '[private absolute path omitted]', value)
        value = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '[private operational identifier omitted]', value)
        value = re.sub(r'(?<!\w)\.local[/\\][^\s`\]"<>]+', '[restricted provenance path]', value)
        return value
    return value


OPERATIONAL_TEXT = re.compile(
    r'working[_ -]sentinel|CODEX_(?:THREAD|SESSION|HOME)|windows-[0-9a-f]{12}|'
    r'workspace_instance|\b[a-z][a-z0-9-]*-(?:windows|linux|macos)-canonical\b|/root/[A-Za-z0-9_/.-]+|'
    r'\.working\b|--human-owner|--session-id|\bwork_id\b|\btask[_ -]?id\b|'
    r'\bsession[_ -]?id\b|actual human|human.owner|\bhuman\s+[a-z][a-z0-9_-]{1,40}\b|ownership claim|'
    r'(?<![A-Za-z0-9])c\d+-[A-Za-z0-9]+-[A-Za-z0-9-]+|subagent.*(?:scope|packet|deadline)|'
    r'(?:owned|exclusive).*write.scope|writer.reservation|structured.claim|'
    r'^\s*(?:[-*|]\s*)?(?:Owner(?: task)?|Host|Session|Checkout|Sentinel|Work ID|Task ID|Human)\s*[:|=]', re.I | re.M)

REVIEWED_OPERATIONAL_SECTIONS = {
    'local-section:'+x for x in (
        '276016fcf07297e0446674f4', 'fa8131d2c6f297e3e8321f40',
        '379810aa02a35c5a2e8e281b', '98b549dcc5c600f568221867',
        '3fcb63c3c9999721d59956a9', '512bbc8403ba12bebbebd820',
        '58cf00035d09f5b7d5741f27', '61fb54d5310c24ebc512a814',
        '869fe859ddecd28c698e33a2', 'aa8c81ddda2998495994d1f0',
        'e74978b00f9c359249aabf1d', 'fd572b730c1ea05dff1f0912')}
REVIEWED_OPERATIONAL_TEXT = re.compile(
    r'PROJECT_STATUS\.md|Git (?:ownership|index|refs|operations)|native task|'
    r'same native conversation|work/session|scope/freeze|freeze (?:bytes|timestamps?)|'
    r'claim acquisition|30.card priority sequence|Owner task.*deadline', re.I)

# Conclusive operational sentences across local research sources. Mixed
# paragraphs keep their mathematical sentences; upstream bodies are untouched.
LOCAL_OPERATIONAL_SENTENCE = re.compile(
    r'native task|Owner task|fresh exact claim|claim (?:was )?acquired|claim is released|'
    r'work/session|effective.generation/cache|(?:model|cache).*telemetry|'
    r'same assigned Astra|Astra Max (?:context|conversation)|assigned ignored directory|'
    r'freeze manifest.*(?:bytes|hashes)|author mathematical STOP|'
    r'controller owns.*(?:admission|changes)|(?:author|review) deadline|'
    r'30.card priority (?:order|sequence)', re.I)


def project_operational_text(value, omissions, rid, field):
    if not isinstance(value, str):
        return value
    if not rid.startswith(('local:', 'local-section:', 'cycle20-', 'review:', 'reviewed-claim:')):
        return value
    blocks = re.split(r'(\n\s*\n)', value)
    kept = []
    for block in blocks:
        if OPERATIONAL_TEXT.search(block) or (rid in REVIEWED_OPERATIONAL_SECTIONS and REVIEWED_OPERATIONAL_TEXT.search(block)):
            omissions.append({'record_id': rid, 'field': field, 'sha256': digest(block.encode()), 'exact_private_block': block, 'reason': 'operational ownership/session/host/process provenance; not public mathematical statement'})
        else:
            sentences = re.split(r'(?<=[.!?])(?=\s)', block)
            for sentence in sentences:
                if LOCAL_OPERATIONAL_SENTENCE.search(sentence):
                    omissions.append({'record_id': rid, 'field': field, 'sha256': digest(sentence.encode()), 'exact_private_block': sentence, 'reason': 'conclusive local operational sentence; mathematical remainder retained'})
                else:
                    kept.append(sentence)
    return ''.join(kept).strip() or None


def project_private_references(value):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key in ('path', 'file', 'inventory') and isinstance(item, str) and item.startswith(('research/', '.local/', 'corpus/')):
                result[key] = 'restricted-source:' + digest(item.encode())[:24]
            else:
                result[key] = project_private_references(item)
        return result
    if isinstance(value, list):
        return [project_private_references(x) for x in value]
    if isinstance(value, str):
        # Preserve immutable public URL bytes even inside source prose.
        parts = re.split(r'(https://[^\s`\]"<>]+)', value)
        return ''.join(part if part.startswith('https://') else re.sub(r'research/[^\s`\]"<>)]*', '[restricted mathematical source]', part) for part in parts)
    return value


def export_public(repo, private, output, config, receipt_path, private_usage=None, base_root=None):
    cat = Catalogue(private)
    coverage = json.loads((private/'coverage.json').read_text(encoding='utf-8'))
    source_map = {}
    def add(path, url, **extra):
        if url:
            source_map[path] = {'url': url, **extra}
    root = repo / LIB
    for row in json.loads((root/'historical/source-file-manifest.json').read_text(encoding='utf-8')):
        immutable = row.get('immutable_source', {})
        add(LIB+'/historical/'+row['payload_path'], immutable.get('url') or immutable.get('source_url') or immutable.get('archive_url'), author_credit=row.get('author_credit'), **{k: v for k, v in immutable.items() if k in ('archive_member', 'archive_sha256', 'source_git_blob')})
    for row in json.loads((root/'local-moments/provenance.json').read_text(encoding='utf-8'))['primary_sources']:
        add(LIB+'/local-moments/'+row['path'], row.get('url'))
    for filename in ('source-manifest.json', 'history-source-manifest.json'):
        for row in json.loads((root/'closed-prs'/filename).read_text(encoding='utf-8'))['sources']:
            add(LIB+'/closed-prs/originals/'+row['name'], row.get('url'))
    for filename in ('source-manifest.json', 'extra-source-manifest.json'):
        for row in json.loads((root/'maintenance'/filename).read_text(encoding='utf-8')):
            add(LIB+'/maintenance/'+row['local'], row.get('url'))
    term_sources = []
    for source_path, item in source_map.items():
        name = Path(item.get('archive_member') or source_path).name.lower()
        if re.search(r'^(?:upstream[_-])?(?:licen[cs]e|notice|copyright)s?(?:\.[a-z]+)?$', name):
            term_sources.append((source_path, item))
    public_records = {}; exclusions = collections.Counter(); usage_rows = []; omissions = []; private_documents = {}; module_authors = {}
    closed_authors = json.loads((root/'closed-prs/unit-inventory.json').read_text(encoding='utf-8'))['authors']
    idmap = {rid: (None if rid.startswith('local-document:') else rid.replace('cycle20-review:', 'review:').replace('cycle20-claim:', 'reviewed-claim:')) for rid in cat.by_id}
    def redact_internal(value):
        if isinstance(value, dict):
            result = {}
            for k, v in value.items():
                if k == 'path' and isinstance(v, str) and v.startswith('research/') and not v.startswith(LIB+'/'):
                    result[k] = 'restricted-mathematical-source'
                else:
                    result[k] = redact_internal(v)
            return result
        if isinstance(value, list):
            return [redact_internal(v) for v in value]
        if isinstance(value, str) and not value.startswith('https://'):
            if value.startswith('research/') and not value.startswith(LIB+'/'):
                return '[restricted mathematical source]'
            value = re.sub(r'research/(?!imports/)[^\s`\]"<>)]*', '[restricted mathematical source]', value)
            value = re.sub(r'\b0[0-6]_CYCLE20_[A-Z_]+\.md\b', '[restricted mathematical source]', value)
            value = re.sub(r'(?i)\bcycle\s*\d+\b', '[research revision]', value)
            value = re.sub(r'\bC[1-9]\d{1,2}\b', '[research revision]', value)
            value = re.sub(r'(?:research/)?(?:cycle\d+|attempts)/[^\s`\]"<>)]*', '[restricted mathematical source]', value, flags=re.I)
            return value
        return value
    for r in cat.iter_records():
        rid = r['id']; original_source = r.get('source_record'); original_origin = r['origin']
        if idmap[rid] is None:
            private_documents[rid] = r['pointers']
            continue
        for field in ('title', 'statement', 'hypotheses', 'quantifier_scope', 'review_status', 'unresolved_prerequisites'):
            r[field] = project_operational_text(r.get(field), omissions, rid, field)
        if r['origin'].startswith('local') or rid.startswith(('local:', 'local-section:', 'cycle20-')):
            usage_rows.append({'public_component_id': idmap[rid], 'private_intake_id': rid, 'usage_class': 'internal-source-occurrence; not proved dependency', 'internal_origin': r['origin'], 'cycles': [t[6:] for t in r['tags'] if t.startswith('cycle:')], 'source_record': r.get('source_record'), 'local_pointers': r['pointers'], 'local_navigation': r['relations']})
            r = redact_internal(r)
            r['origin'] = 'qrh-mathematical-library'
            r['tags'] = [t for t in r['tags'] if not t.startswith('cycle:')]
            if r['kind'] == 'research-section':
                r['kind'] = 'mathematical-source-section'
        if not r['title']:
            r['title'] = 'Restricted provenance locator'
        r['review_status'] = r['review_status'] or 'unknown'
        if r['kind'] == 'mathematical-source-section' and not r['statement']:
            r['kind'] = 'restricted-provenance-locator'
        r['id'] = idmap[rid]
        if r.get('semantic_component_id'):
            r['semantic_component_id'] = idmap.get(r['semantic_component_id'], r['semantic_component_id'])
        r['relations'] = [{**edge, 'target': idmap[edge['target']], 'evidence': redact_internal(edge['evidence'])} for edge in r['relations'] if idmap.get(edge['target'])]
        raw = r.get('raw_source_record')
        formal = r.get('formal_component')
        if formal and raw and not raw.get('fully_qualified_name') and formal.get('namespace') is None and formal.get('fully_qualified_name') == raw.get('name'):
            formal['fully_qualified_name'] = None
            formal['qualification'] += ' Exact namespace/full qualification is unknown; literal source declaration name is retained.'
        if r['author']:
            module_authors[rid] = r['author']
        elif raw and raw.get('module_id') in module_authors:
            r['author'] = module_authors[raw['module_id']]
            r['evidence']['author'] = {'basis': 'literal-owning-module-inventory-credit', 'module_id': raw['module_id']}
        elif raw and raw.get('pr') in (7,30):
            r['author'] = closed_authors['pr'+str(raw['pr'])]
            r['evidence']['author'] = {'basis': 'literal-collection-author-credit', 'inventory': LIB+'/closed-prs/unit-inventory.json', 'json_pointer': '/authors/pr'+str(raw['pr'])}
        if rid.startswith('pr15:AllHeightDensity'):
            r['author'] = "Mathematical height split: Zhongpai Gao, prepared with AI assistance; surrounding mathematical development: OpenAI, Hailey Collet and Akash Levy. Incremental formalization prepared with AI assistance; Mathlib retains its authorship."
            r['evidence']['author'] = {'basis': 'literal-source-notice-credit', 'url': source_map[LIB+'/local-moments/sources/pr15/NOTICE.md']['url']}
        if raw:
            exclusions.update(set(raw)-PUBLIC_RAW_FIELDS)
            r['raw_source_record'] = {k: v for k, v in raw.items() if k in PUBLIC_RAW_FIELDS}
            for field, value in list(r['raw_source_record'].items()):
                if isinstance(value, str):
                    r['raw_source_record'][field] = project_operational_text(value, omissions, rid, 'raw_source_record/'+field)
            # Exact mathematical text is retained once in the normalized fields;
            # full raw row remains losslessly identified in restricted intake.
            promoted = {}
            for target, candidates in [('statement', ('statement','statement_and_explicit_quantifiers','statement_excerpt','claim','audited_disposition','disposition')), ('hypotheses', ('assumptions','assumption_contract','assumption_context','full_relevant_assumptions_quantifiers','qualification')), ('quantifier_scope', ('full_assumptions_quantifiers','contract_scope','full_relevant_assumptions_quantifiers'))]:
                for field in candidates:
                    if field in r['raw_source_record'] and r.get(target) == r['raw_source_record'][field]:
                        del r['raw_source_record'][field]; promoted[field] = target
            r['evidence']['public_projection'] = {'basis': 'explicit-public-mathematical-field-projection', 'promoted_fields': promoted, 'omitted_raw_fields': sorted(set(raw)-PUBLIC_RAW_FIELDS)}
        r = public_safe(r)
        for p in r['pointers']:
            original = p.get('path')
            if original in source_map:
                p.update(source_map[original])
                if not r['author'] and source_map[original].get('author_credit'):
                    r['author'] = source_map[original]['author_credit']
                    r['evidence']['author'] = {'basis': 'literal-source-manifest-credit', 'public_source': p['url']}
            p['access'] = 'public-primary-source' if p.get('url') else 'restricted-source'
            if not p.get('url'):
                if re.match(r'research/(?:cycle\d+|attempts|attempt-index|current-proof|review-cycle)', p.get('path') or ''):
                    usage_rows.append({'public_component_id': r['id'], 'private_intake_id': rid, 'usage_class': 'internal-library-navigation; not proved dependency', 'internal_origin': original_origin, 'cycles': re.findall(r'cycle(\d+)', p['path']), 'source_record': original_source, 'local_pointers': [dict(p)], 'local_navigation': []})
                    p['path'] = 'restricted-mathematical-source'
                p['source_label'] = 'restricted source '+(p.get('sha256') or digest(str(original).encode()))[:16]
            elif r.get('formal_component'):
                m = re.match(r'https://(?:raw\.githubusercontent\.com|github\.com)/([^/]+/[^/]+)/(?:blob/)?([0-9a-f]{40})/(.+?)(?:#.*)?$', p['url'])
                if m:
                    r['formal_component']['repository'] = 'https://github.com/'+m[1]
                    r['formal_component']['source_ref'] = m[2]
                    r['formal_component']['path'] = p.get('archive_member') or m[3]
                    r['source_revision'] = r['source_revision'] or m[2]
                    p['path'] = p.get('archive_member') or m[3]
                elif p.get('archive_member'):
                    p['path'] = p['archive_member']
            elif p.get('archive_member'):
                p['path'] = p['archive_member']
        # Terms belong to each source. No new license for upstream mathematics.
        handling = (raw or {}).get('license_handling')
        source_urls = [p.get('url','') for p in r['pointers']]
        notice_refs = []
        for source_path, item in term_sources:
            if any(item['url'].rsplit('/',1)[0] in url for url in source_urls):
                notice_refs.append({'url': item['url'], 'archive_member': item.get('archive_member'), 'archive_sha256': item.get('archive_sha256'), 'source_label': item.get('archive_member') or unquote(item['url'].split('/')[-1])})
        notice_refs = sorted({compact(x): x for x in notice_refs}.values(), key=compact)
        notice_urls = sorted(set(x['url'] for x in notice_refs))
        r['source_terms'] = {'license_status': 'source-specific; no blanket relicense', 'attribution': r['author'], 'license_and_notice_urls': notice_urls, 'license_and_notice_references': notice_refs, 'handling': handling or 'Original author notices and upstream licenses control; no proof bodies copied by public export.', 'inventory_evidence': r.get('source_record')}
        if r.get('raw_source_record') and isinstance(r['raw_source_record'].get('dependencies'), dict):
            deps = r['raw_source_record']['dependencies']
            if 'existing_library' in deps:
                deps['existing_library'] = [redact_internal(x) for x in deps['existing_library']]
        public_records[r['id']] = project_private_references(r)
    artifact_links = []
    # PRs are public submissions/records, with captured status bound to snapshot.
    for r in public_records.values():
        if r['id'].startswith('upstream:PR'):
            raw = r['raw_source_record']
            r['kind'] = 'public-submission'
            r['public_artifact'] = {'artifact_kind': 'record-submission', 'public_url': 'https://github.com/GTimG/QuasiRiemannTracker/pull/'+r['id'].split('PR')[1], 'version': raw.get('head_sha'), 'status': raw.get('state', 'unknown'), 'status_basis': 'frozen 2026-10-13 source snapshot; no live claim', 'repository': raw.get('head_repo'), 'paper_or_leaderboard_id': None}
        for p in r['pointers']:
            url = p.get('url')
            member = p.get('archive_member', '')
            if url and (url.split('#')[0].lower().endswith(('.tex', '.pdf')) or member.lower().endswith('.tex')):
                aid = 'public-artifact:' + digest((url+'\0'+member).encode())[:24]
                artifact_links.append((r['id'], aid, p))
    for source, aid, p in artifact_links:
        if aid not in public_records:
            a = Builder(repo, output, config).record(aid, p.get('archive_member') or unquote(p['url'].split('/')[-1]), 'public-paper', 'public-primary-source')
            a['pointers'] = [p]
            a['public_artifact'] = {'artifact_kind': 'paper-or-manuscript-source', 'public_url': p['url'], 'version': next((x for x in p['url'].split('/') if re.fullmatch('[0-9a-f]{40}', x)), None), 'status': 'public source identified; publication/referee status unknown', 'section_or_theorem_locator': None}
            a['source_terms'] = {'license_status': 'original source terms; no blanket relicense', 'handling': 'Source pointer only; no original proof body copied as paper artifact'}
            public_records[aid] = a
        evidence = {'public_url': p['url'], 'archive_member': p.get('archive_member'), 'line_start': p.get('line_start'), 'line_end': p.get('line_end'), 'source_sha256': p.get('sha256'), 'use_status': 'documented-statement-or-locator-occurrence; derivation reuse not inferred'}
        public_records[source]['relations'].append({'target': aid, 'kind': 'appears_in', 'basis': 'explicit-public-source-location', 'evidence': [evidence]})
        public_records[aid]['relations'].append({'target': source, 'kind': 'contains_statement_occurrence', 'basis': 'inverse-explicit-public-source-location', 'evidence': [evidence]})
    # Reference-only papers keep credit without republishing unlicensed bodies.
    for raw in json.loads((root/'historical/liu-manuscript-manifest.json').read_text(encoding='utf-8')):
        aid = 'public-paper:' + raw['id']
        a = Builder(repo, output, config).record(aid, raw['path'], 'public-paper', 'public-primary-source')
        a['author'] = raw['author']; a['source_revision'] = raw['commit']
        a['pointers'] = [{'url': raw['url'], 'sha256': raw['sha256'], 'access': 'public-primary-source', 'role': 'reference-only-paper'}]
        a['public_artifact'] = {'artifact_kind': 'paper', 'public_url': raw['url'], 'version': raw['commit'], 'status': 'public manuscript; publication/referee status unknown'}
        a['source_terms'] = {'license_status': 'No redistribution license identified', 'handling': raw['redistribution'], 'attribution': raw['author']}
        public_records[aid] = a
    # Repeated exact pointers retain their evidence while directed edges stay
    # unique. This is necessary for owner export and standalone refresh parity.
    for r in public_records.values():
        unique = {}
        for e in r['relations']:
            key = (e['kind'], e['target'])
            merged = unique.setdefault(key, {**e, 'evidence': []})
            for ev in e.get('evidence', []):
                if ev not in merged['evidence']:
                    merged['evidence'].append(ev)
        r['relations'] = [unique[key] for key in sorted(unique)]
    output.mkdir(parents=True, exist_ok=True)
    entries = []; offsets = {}; ids = sorted(public_records); files = []
    (output/'data').mkdir(exist_ok=True)
    shard = 1; shard_path = 'data/records-0001.jsonl'; files.append(shard_path)
    with (output/shard_path).open('wb') as initial:
        f = initial
        for pos, rid in enumerate(ids):
            r = public_records[rid]; line = (compact(r)+'\n').encode()
            if f.tell()+len(line) > 16*1024*1024:
                f.close(); shard += 1; shard_path = f'data/records-{shard:04d}.jsonl'; files.append(shard_path); f = (output/shard_path).open('wb')
            offsets[rid] = {'file': shard_path, 'offset': f.tell(), 'bytes': len(line)}; f.write(line)
            text = '\n'.join(str(r.get(k) or '') for k in ('title', 'statement', 'hypotheses', 'quantifier_scope', 'review_status'))
            entries.append({k: r[k] for k in ('id', 'aliases', 'title', 'kind', 'origin', 'mathematical_status', 'review_status', 'formalization_status', 'status_labels', 'conditional', 'source_relative', 'tags', 'topics', 'methods', 'objects')} | {'search_text': text.casefold(), 'page': 'records/'+f'{pos//100+1:04d}.md'+'#'+slug(rid)})
        f.close()
    edges = []
    for r in public_records.values():
        for edge in r['relations']:
            edges.append({'source': r['id'], **edge})
    edges.sort(key=lambda e: (e['source'], e['kind'], e['target']))
    write_json(output/'index.json', {'schema_version': VERSION, 'entries': entries, 'offsets': offsets, 'edges': edges, 'record_files': files})
    public_coverage = public_safe(coverage)
    public_coverage['records'] = len(public_records); public_coverage['edges'] = len(edges)
    public_coverage['counts_by_kind'] = dict(sorted(collections.Counter(r['kind'] for r in public_records.values()).items()))
    projected_inputs = {}
    for path, input_receipt in public_coverage['inputs'].items():
        projected = dict(input_receipt)
        projected['roles'] = ['mathematical-intake-reference']
        projected['groups'] = {}
        for group, counts in input_receipt['groups'].items():
            mapped = [idmap[x] for x in counts['record_ids'] if idmap.get(x)]
            projected['groups'][group] = {'expected': len(mapped), 'represented': len(mapped), 'record_ids': mapped, 'excluded_navigation_nodes': len(counts['record_ids'])-len(mapped)}
        projected_inputs['restricted-source:'+input_receipt['sha256']+'-'+digest(path.encode())[:12]] = projected
    public_coverage['inputs'] = projected_inputs
    public_coverage['local_components'] = {k: idmap[v] for k, v in coverage['local_components'].items() if idmap.get(v)}
    public_coverage['records_sha256'] = records_digest([output/p for p in files])
    public_coverage['public_projection'] = {'version': 1, 'raw_mathematical_fields': sorted(PUBLIC_RAW_FIELDS), 'excluded_raw_field_counts': dict(sorted(exclusions.items())), 'full_intake_access': 'source custodian retains exact original rows and input hashes; not publicly available', 'external_sources_fetched': False}
    # Mapping issues may mention internal paths; preserve only mathematical missing-pointer categories publicly.
    public_coverage['issues'] = [{'kind': x['kind'], 'path': public_safe(x.get('path', '')), 'access': 'restricted-source-follow-up'} for x in coverage['issues']]
    write_json(output/'coverage.json', public_coverage)
    renderer = Builder(repo, output, config); renderer.public = True; renderer.records = public_records; renderer.local_components = public_coverage['local_components']; renderer.browse(entries)
    write_json(receipt_path, {'private_records_sha256': coverage['records_sha256'], 'public_records_sha256': public_coverage['records_sha256'], 'record_ids_preserved': ids, 'excluded_raw_field_counts': dict(sorted(exclusions.items())), 'source_map': source_map, 'operational_text_omissions': omissions, 'scope': 'Public mathematical metadata projection; full raw rows and omitted operational blocks remain privately retained'})
    if private_usage:
        private_usage.mkdir(parents=True, exist_ok=True)
        (private_usage/'usage.jsonl').write_text(''.join(compact(r)+'\n' for r in usage_rows), encoding='utf-8', newline='\n')
        write_json(private_usage/'source-crosswalk.json', {'schema_version': 1, 'purpose': 'private usage/provenance only; public component records own mathematical truth', 'private_to_public_id': idmap, 'private_source_documents': private_documents})
    if base_root:
        # Explicit owner installation of the reviewed public projection. Refresh
        # consumes this base; updating generated data alone cannot update it.
        base = base_root/'base-data'; base.mkdir(parents=True, exist_ok=True)
        expected = {Path(p).name for p in files}
        for p in files:
            shutil.copyfile(output/p, base/Path(p).name)
        for path in base.glob('records-*.jsonl'):
            if re.fullmatch(r'records-\d{4}\.jsonl', path.name) and path.name not in expected:
                if not path.resolve().is_relative_to(base_root.resolve()):
                    raise ValueError('Base shard escapes output root:'+str(path))
                path.unlink()
        write_json(base_root/'base-coverage.json', public_coverage)
    return {'records': len(ids), 'edges': len(edges), 'public_sources_mapped': len(source_map), 'public_output': str(output), 'public_base_installed': bool(base_root)}


def validate_contribution(root):
    """Data-only PR gate: never import or run code from the supplied checkout."""
    failures = []
    annotations = json.loads(checked_file(root, 'annotations.json').read_text(encoding='utf-8'))
    if annotations.get('schema_version') != VERSION:
        failures.append('annotations schema_version must be 1')
    ids = set(Catalogue(root/'generated').by_id) if (root/'generated/index.json').is_file() else set()
    component_count = 0; seen_components = set()
    for n, line in enumerate(checked_file(root, 'components.jsonl').read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        r = json.loads(line); component_count += 1
        if r.get('id') in seen_components:
            failures.append('duplicate contributed component ID:'+str(r.get('id')))
        seen_components.add(r.get('id'))
        if not all(r.get(k) for k in ('id', 'title', 'kind')):
            failures.append('component missing id/title/kind at line '+str(n))
        if not r.get('evidence') or not r.get('pointers'):
            failures.append('new component needs evidence and source pointers:'+str(r.get('id')))
        formal = r.get('formal_component') or {}
        for stage, claim in formal.get('verification', {}).items():
            if stage != 'source_reported' and claim.get('status') not in (None, 'unknown', 'not-run'):
                exact_ref = isinstance(formal.get('source_ref'), str) and bool(re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', formal['source_ref']))
                if not exact_ref or claim.get('source_revision') != formal.get('source_ref') or not claim.get('evidence'):
                    failures.append('formal claim needs same exact source revision and evidence:'+str(r.get('id'))+'/'+stage)
        ids.add(r.get('id'))
    for rid, fields in annotations.get('records', {}).items():
        if rid not in ids:
            failures.append('unknown annotation record:'+rid)
        for field, annotation in fields.items():
            if field in ('id', 'raw_source_record', 'source_record', 'relations', 'identity_kind') or not isinstance(annotation, dict) or 'value' not in annotation or not annotation.get('evidence'):
                failures.append('invalid/evidenceless annotation:'+rid+'/'+field)
    allowed = {'contains', 'has_occurrence', 'mentions', 'related', 'reviews', 'exact_source_match', 'depends_on', 'equivalent', 'supersedes', 'superseded_by', 'formalizes', 'implements', 'imports', 'appears_in', 'contains_statement_occurrence', 'documented_use', 'mentioned_in', 'claimed_use'}
    for edge in annotations.get('relations', []):
        if not edge.get('evidence') or edge.get('kind') not in allowed or edge.get('source') not in ids or edge.get('target') not in ids:
            failures.append('invalid/evidenceless relation:'+compact(edge))
        if edge.get('kind') in ('documented_use', 'mentioned_in', 'claimed_use'):
            ev = edge.get('evidence', {})
            if not isinstance(ev, dict) or not ev.get('public_url') or not any(ev.get(k) for k in ('section', 'theorem', 'declaration', 'line_start', 'locator')):
                failures.append('public use link needs public URL and exact locator:'+compact(edge))
    return {'ok': not failures, 'schema_version': VERSION, 'new_components': component_count, 'annotated_records': len(annotations.get('records', {})), 'relations': len(annotations.get('relations', [])), 'failures': failures, 'evidence_class': 'data/schema validation only; not proof acceptance'}


def refresh(root, output):
    """Rebuild public catalogue using only its public base and maintained data."""
    builder = Builder(root, output, root); builder.public = True
    base_coverage = json.loads((root/'base-coverage.json').read_text(encoding='utf-8'))
    builder.inputs = base_coverage['inputs']; builder.local_components = base_coverage['local_components']
    builder.issues = base_coverage.get('issues', [])
    base_files = sorted((root/'base-data').glob('*.jsonl')) if (root/'base-data').is_dir() else [root/'base-records.jsonl']
    for base_file in base_files:
      with base_file.open(encoding='utf-8') as f:
        for line in f:
            if line.strip():
                r = public_safe(json.loads(line)); builder.records[r['id']] = r
                for edge in r['relations']:
                    for evidence in edge.get('evidence', [{}]):
                        builder.edge(r['id'], edge['target'], edge['kind'], evidence, edge['basis'])
                r['relations'] = []
    builder.overlays(); builder.enrich()
    receipt = builder.emit()
    # Emit is shared with the private owner build; split the public record stream
    # into bounded shards and rewrite offsets without changing logical bytes.
    idx = json.loads((output/'index.json').read_text(encoding='utf-8'))
    (output/'data').mkdir(exist_ok=True); shard=1; path='data/records-0001.jsonl'; paths=[path]
    with (output/path).open('wb') as initial:
        f=initial
        with (output/'records.jsonl').open('rb') as src:
            for line in src:
                if f.tell()+len(line)>16*1024*1024:
                    f.close(); shard+=1;path=f'data/records-{shard:04d}.jsonl';paths.append(path);f=(output/path).open('wb')
                rid=json.loads(line)['id'];idx['offsets'][rid]={'file':path,'offset':f.tell(),'bytes':len(line)};f.write(line)
        f.close()
    idx['record_files']=paths;write_json(output/'index.json',idx)
    (output/'records.jsonl').unlink()
    receipt['public_projection'] = base_coverage.get('public_projection')
    write_json(output/'coverage.json', receipt)
    return {'records': receipt['records'], 'edges': receipt['edges'], 'output': str(output)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    build = sub.add_parser('build'); build.add_argument('--repo', type=Path, required=True); build.add_argument('--output', type=Path, required=True); build.add_argument('--config', type=Path, default=Path(__file__).resolve().parent)
    check = sub.add_parser('validate'); check.add_argument('--repo', type=Path); check.add_argument('--catalogue', type=Path, default=Path(__file__).resolve().parent/'generated')
    export = sub.add_parser('export-public'); export.add_argument('--repo', type=Path, required=True); export.add_argument('--private-catalogue', type=Path, required=True); export.add_argument('--output', type=Path, required=True); export.add_argument('--private-receipt', type=Path, required=True); export.add_argument('--private-usage', type=Path); export.add_argument('--base-root', type=Path)
    contribution = sub.add_parser('validate-contribution'); contribution.add_argument('--root', type=Path, required=True)
    rebuilding = sub.add_parser('refresh'); rebuilding.add_argument('--root', type=Path, default=Path(__file__).resolve().parent); rebuilding.add_argument('--output', type=Path)
    for command in ('query', 'show', 'traverse'):
        p = sub.add_parser(command); p.add_argument('--catalogue', type=Path, default=Path(__file__).resolve().parent/'generated')
        if command == 'query':
            p.add_argument('text', nargs='*'); p.add_argument('--json', action='store_true'); p.add_argument('--limit', type=int, default=30)
            for field in ('kind', 'origin', 'status', 'tag', 'topic', 'method', 'object', 'review', 'formalization'):
                p.add_argument('--'+field, action='append')
            p.add_argument('--conditional', action='store_true'); p.add_argument('--source-relative', action='store_true')
        else:
            p.add_argument('--id', required=True)
        if command == 'traverse':
            p.add_argument('--relation', action='append'); p.add_argument('--direction', choices=('in', 'out', 'both'), default='both'); p.add_argument('--depth', type=int, default=1)
    args = parser.parse_args()
    try:
        if args.command == 'build':
            receipt = Builder(args.repo.resolve(), args.output.resolve(), args.config.resolve()).build()
            print(compact({'records': receipt['records'], 'edges': receipt['edges'], 'issues': len(receipt['issues']), 'output': str(args.output)}))
        elif args.command == 'validate':
            result = validate(args.repo.resolve() if args.repo else None, args.catalogue.resolve()); print(json.dumps(result, ensure_ascii=False, indent=2)); return 0 if result['ok'] else 1
        elif args.command == 'validate-contribution':
            result = validate_contribution(args.root.resolve()); print(json.dumps(result, ensure_ascii=False, indent=2)); return 0 if result['ok'] else 1
        elif args.command == 'export-public':
            print(compact(export_public(args.repo.resolve(), args.private_catalogue.resolve(), args.output.resolve(), Path(__file__).resolve().parent, args.private_receipt.resolve(), args.private_usage.resolve() if args.private_usage else None, args.base_root.resolve() if args.base_root else None)))
        elif args.command == 'refresh':
            print(compact(refresh(args.root.resolve(), (args.output or args.root/'generated').resolve())))
        else:
            cat = Catalogue(args.catalogue)
            if args.command == 'show':
                print(json.dumps(cat.record(args.id), ensure_ascii=False, indent=2))
            elif args.command == 'traverse':
                print(json.dumps(cat.traverse(args.id, args.relation, args.direction, args.depth), ensure_ascii=False, indent=2))
            else:
                result = cat.query(args)
                if args.json:
                    print(json.dumps({'total': len(result), 'records': result[:args.limit]}, ensure_ascii=False, indent=2))
                else:
                    for r in result[:args.limit]:
                        print(f'{r["id"]}\t{r["kind"]}\t{r["title"]}')
                    print(f'{len(result)} matches; showing {min(len(result), args.limit)}')
        return 0
    except (ValueError, KeyError, FileNotFoundError) as error:
        print(str(error), file=sys.stderr); return 2


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
