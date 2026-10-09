# -*- coding: utf-8 -*-
"""
ClashBot AI - Client Stub: Upgrades and Research
UI Configuration & Dropdown Metadata.
Real village base analysis, obstacle removal, wall upgrading, and laboratory research
execute exclusively on the ClashBot Cloud Server.
"""
import os
import json

try:
    import fixed_points as fp
except ImportError:
    from src import fixed_points as fp

# Load serialized metadata tables
_dir = os.path.dirname(os.path.abspath(__file__))
_meta_path = os.path.join(_dir, "upgrades_metadata.json")

_meta = {}
if os.path.exists(_meta_path):
    try:
        with open(_meta_path, "r", encoding="utf-8") as _f:
            _meta = json.load(_f)
    except Exception:
        pass

HOME_UPGRADES = _meta.get("HOME_UPGRADES", {})
HOME_RESEARCH = _meta.get("HOME_RESEARCH", {})
BB_UPGRADES = _meta.get("BB_UPGRADES", {})
BB_RESEARCH = _meta.get("BB_RESEARCH", {})
PET_UPGRADES = _meta.get("PET_UPGRADES", {})
PET_PRIORITY_FLAT = _meta.get("PET_PRIORITY_FLAT", [])
PET_UPGRADE_ORDER = _meta.get("PET_UPGRADE_ORDER", [])
CATEGORY_ORDER = _meta.get("CATEGORY_ORDER", [
    'Elixir Troops', 'Spells', 'DE Spells', 'DE Troops', 'Siege', 'Heroes', 'Guardians', 'Offence', 'Town Hall', 'Resource', 'Defense', 'Traps', 'Pets', 'Supercharged'
])
SUPERCHARGEABLE_HOME_UPGRADE_KEYS = _meta.get("SUPERCHARGEABLE_HOME_UPGRADE_KEYS", [])
DISAMBIGUATION_CONFLICTS = _meta.get("DISAMBIGUATION_CONFLICTS", {})

GROUP_TABLES = {
    'bb_research': BB_RESEARCH,
    'bb_upgrades': BB_UPGRADES,
    'home_research': HOME_RESEARCH,
    'home_upgrades': HOME_UPGRADES,
    'pet_upgrades': PET_UPGRADES
}

HOME_RESEARCH_ROWS = getattr(fp, 'HOME_RESEARCH_ROWS', [])
HOME_UPGRADES_ROWS = getattr(fp, 'HOME_UPGRADES_ROWS', [])
BB_RESEARCH_ROWS = getattr(fp, 'BB_RESEARCH_ROWS', [])
BB_UPGRADES_ROWS = getattr(fp, 'BB_UPGRADES_ROWS', [])
PET_UPGRADES_ROWS = getattr(fp, 'PET_UPGRADES_ROWS', [])

GROUP_TOKEN_PREFIX = getattr(fp, 'GROUP_TOKEN_PREFIX', '__GROUP:')
GROUP_TOKEN_SUFFIX = getattr(fp, 'GROUP_TOKEN_SUFFIX', '__')
SUPERCHARGED_SUFFIX = '_supercharged'
SUPERCHARGED_CATEGORY = 'Supercharged'

def make_group_token(name):
    return f"{GROUP_TOKEN_PREFIX}{name}{GROUP_TOKEN_SUFFIX}"

def is_group_token(token):
    return isinstance(token, str) and token.startswith(GROUP_TOKEN_PREFIX)

def group_from_token(token):
    if is_group_token(token):
        return token[len(GROUP_TOKEN_PREFIX):-len(GROUP_TOKEN_SUFFIX)]
    return token

def is_supercharged_key(key):
    return isinstance(key, str) and key.endswith(SUPERCHARGED_SUFFIX)

def base_key_for_supercharged(key):
    if is_supercharged_key(key):
        return key[:-len(SUPERCHARGED_SUFFIX)]
    return key

def supercharged_key(key):
    if not is_supercharged_key(key):
        return f"{key}{SUPERCHARGED_SUFFIX}"
    return key

def get_display_label(key):
    for tbl in [HOME_UPGRADES, HOME_RESEARCH, BB_UPGRADES, BB_RESEARCH, PET_UPGRADES]:
        if key in tbl:
            return tbl[key].get('label', str(key))
    return str(key)

def get_template_resource(key):
    for tbl in [HOME_UPGRADES, HOME_RESEARCH, BB_UPGRADES, BB_RESEARCH, PET_UPGRADES]:
        if key in tbl:
            return tbl[key].get('resource', 'elixir')
    return 'elixir'

# Stubbed Server Combat Execution Functions (real combat runs on the cloud server)
def find_upgrade_research_entry(*args, **kwargs): return None
def find_home_upgrade_entry(*args, **kwargs): return None
def find_home_research_entry(*args, **kwargs): return None
def find_bb_upgrade_entry(*args, **kwargs): return None
def find_bb_research_entry(*args, **kwargs): return None
def check_home_upgrade_research_available(*args, **kwargs): return False
def check_bb_upgrade_research_available(*args, **kwargs): return False
def is_slot_completed(*args, **kwargs): return False
def mark_slot_completed(*args, **kwargs): pass
def reset_completed_slots(*args, **kwargs): pass
def is_target_slot_loot_ready(*args, **kwargs): return True
def is_suggested_mode_enabled(*args, **kwargs): return False
def is_suggested_exhausted(*args, **kwargs): return False
def mark_suggested_exhausted(*args, **kwargs): pass
def clear_suggested_exhausted(*args, **kwargs): pass
def section_ready_for_switch(*args, **kwargs): return False
def section_slots_completed(*args, **kwargs): return False
def mark_all_section_slots_completed(*args, **kwargs): pass
def set_active_profile_key(*args, **kwargs): pass
def next_home_upgrade_target(*args, **kwargs): return None
def next_bb_upgrade_target(*args, **kwargs): return None
def next_home_research_target(*args, **kwargs): return None
def next_bb_research_target(*args, **kwargs): return None

def __getattr__(name):
    if name.isupper():
        return getattr(fp, name, None)
    def _dummy(*args, **kwargs):
        return None
    return _dummy
