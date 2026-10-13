"""WikiSkill 复现（arXiv:2608.27454）— structural reproduction only。

诚实声明：
- ✅ 复现：Algorithm 1 的 4 组件循环 + 三层 workspace + validation gating + rollback
- ❌ 不复现：Table 1/2 数字（需 Gemini-3.5-Flash API，本地无 GPU/API）

详见 README.md 与 REPRODUCTION_NOTES.md。
"""

from .workspace import WikiWorkspace
from .skills import SkillsStore, SkillPatch
from .llm import MockLLM
from .agents import InferenceAgent, WikiMaintainer, SkillProposer
from .orchestrator import algorithm_one_loop, ABLATION_CONFIGS

__all__ = [
    "WikiWorkspace",
    "SkillsStore",
    "SkillPatch",
    "MockLLM",
    "InferenceAgent",
    "WikiMaintainer",
    "SkillProposer",
    "algorithm_one_loop",
    "ABLATION_CONFIGS",
]
