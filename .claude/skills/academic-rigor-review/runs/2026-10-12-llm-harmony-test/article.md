# LLM Harmony: Multi-Agent Communication for Problem Solving
# (Test article for academic-rigor-review skill)

**Authors:** Sumedh Rasal (Georgia Institute of Technology)
**arXiv:** 2401.01312
**Date:** January 2, 2024
**Subject:** Multiagent Systems (cs.MA)
**Repository:** https://github.com/sumedhrasal/simulation
**License:** CC BY-SA 4.0

> **NOTE on data**: This test article was reconstructed from WebFetch summaries
> (the WebFetch tool returned summaries rather than verbatim text). All quotes
> below are the tool's summary output, not verbatim from the paper. The
> smoke test is therefore more demanding than a full-text review:
> P1/P2 must work under incomplete information.

## Abstract (as reported by WebFetch)

"Large Language Models (LLMs) have revolutionized Natural Language Processing but
exhibit limitations, particularly in autonomously addressing novel challenges such
as reasoning and problem-solving. Traditional techniques like chain-of-thought
prompting necessitate explicit human guidance. This paper introduces a novel
multi-agent communication framework, inspired by the CAMEL model, to enhance
LLMs' autonomous problem-solving capabilities. The framework employs multiple
LLM agents, each with a distinct persona, engaged in role-playing communication,
offering a nuanced and adaptable approach to diverse problem scenarios.
Extensive experimentation demonstrates the framework's superior performance and
adaptability, providing valuable insights into the collaborative potential of
multiple agents in overcoming the limitations of individual models."

## Core Innovation (as reported by WebFetch)

A multi-agent communication framework using multiple LLM agents with distinct
personas engaged in role-playing communication to enhance autonomous
problem-solving capabilities.

## Key Contributions (as reported by WebFetch)

- Novel framework employing multiple LLM agents with unique personas
- Leverages chain-of-thought prompting for structured reasoning
- Built on CAMEL's architecture with adaptability to various problem types

## Methodology (as reported by WebFetch)

The framework assigns distinct personas to agents (e.g., "Student" and "Teacher")
and provides tailored chain-of-thought prompts. This enables multi-agent
collaboration where agents validate each other's responses, mitigating
hallucination and improving cooperation.

## Experimental Results (as reported by WebFetch)

| Dataset           | Single Agent | Multi-Agent | Our Approach |
| ----------------- | ------------ | ----------- | ------------ |
| GSM8K (Arithmetic)| 50%          | 55%         | 65%          |
| SVAMP (Arithmetic)| 70%          | 73%         | 77%          |
| CSQA (Commonsense)| 77%          | 78%         | 83%          |

## Limitations (as reported by WebFetch)

- Context window constraints per agent
- Requires diverse training data for improved reasoning
- No mechanism for incorporating new information

## Conclusion (as reported by WebFetch)

The proposed framework demonstrates significant improvements in arithmetic
reasoning and commonsense understanding, offering a cost-effective alternative
to model retraining while reducing reliance on human intervention.

## Reference (mentioned in summary)

- CAMEL model: not described in detail in the summary

## Notes for Skill Testing

This article is intentionally reconstructed from summary. The skill should:
- P1: extract claims even with limited information
- P2: flag missing/unverifiable citations (no full reference list available)
- P3: identify logical gaps in the experimental comparison
- P4: audit the experimental setup (which models? which prompts? which seeds?)
- P5: find counter-arguments P2-P4 may have missed
- P6: integrate the above and give a verdict
