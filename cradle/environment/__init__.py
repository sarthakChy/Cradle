from importlib import import_module

from .skill_registry import SkillRegistry
from .ui_control import UIControl
from .skill import Skill, post_skill_wait
from .utils import serialize_skills, deserialize_skills


_LAZY_EXPORTS = {
    "SoftwareUIControl": ".software.ui_control",
    "SoftwareSkillRegistry": ".software.skill_registry",
    "CapCutSkillRegistry": ".capcut.skill_registry",
    "ChromeSkillRegistry": ".chrome.skill_registry",
    "FeishuSkillRegistry": ".feishu.skill_registry",
    "OutlookSkillRegistry": ".outlook.skill_registry",
    "RDR2SkillRegistry": ".rdr2.skill_registry",
    "RDR2UIControl": ".rdr2.ui_control",
    "SkylinesSkillRegistry": ".skylines.skill_registry",
    "SkylinesUIControl": ".skylines.ui_control",
    "DealersSkillRegistry": ".dealers.skill_registry",
    "DealersUIControl": ".dealers.ui_control",
    "StardewSkillRegistry": ".stardew.skill_registry",
    "StardewUIControl": ".stardew.ui_control",
    "XiuxiuSkillRegistry": ".xiuxiu.skill_registry",
}


def __getattr__(name):
    if name in _LAZY_EXPORTS:
        module = import_module(_LAZY_EXPORTS[name], __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
