---
name: starwave:requirements
description: 1. Requirement Gathering
---

### 1. Requirement Gathering

First, generate an initial set of requirements in EARS format based on the feature idea, then iterate with the user to refine them until they are complete and accurate.

Don't focus on code exploration in this phase. Instead, just focus on writing requirements which will later be turned into
a design.

**Writing Style — Signal over Volume:**

Requirements describe what the system must do and why, in the minimum words needed for each to be testable. They are not a design document, not a tutorial, and not a restatement of the user's prompt.

- The introduction MUST be 2-4 sentences summarizing the feature and its motivation. Do not rephrase the acceptance criteria that follow.
- User stories MUST fit on one line each. Do not expand them into paragraphs.
- Each acceptance criterion MUST describe observable behavior, not implementation. Use outcome language ("SHALL return X given Y") rather than mechanism language ("SHALL use hook Z", "SHALL be implemented as a service", "SHALL use library W"). The design phase decides the how.
- The model MUST NOT add speculative or "future-proofing" requirements. If a capability is not needed for this feature, it is not a requirement.
- The model MUST NOT split one behavioral check into multiple ACs (e.g., separate "accepts", "processes", "returns" bullets for a single operation). Combine into one testable outcome.
- Non-functional requirements (performance, security, accessibility, compatibility) MUST state a concrete, measurable target tied to this feature, or MUST be omitted. Generic bullets like "SHALL be secure" or "SHALL be performant" add nothing and MUST NOT be written.
- The model MUST NOT use hyperbolic or marketing language ("comprehensive", "robust", "seamless", "powerful").

**Constraints:**

- The model MUST first propose a {feature_name} based on: (1) user's explicit preference if stated, (2) current branch name if not a default branch like main or develop, (3) derived from the prompt content. The model MUST allow the user to override this proposal.
- The model MUST wait for the user's answer to the {feature_name} question.
- Once the {feature_name} is decided, the model MUST first ask general questions that are important to the requirements. This includes, but is not limited to, backwards compatibility.
- The model MUST create a 'specs/{feature_name}/requirements.md' file if it doesn't already exist
- Unless told differently by the user, the model MUST ask clarifying questions around the proposed solution.
- The model MUST keep asking questions, until everything is clear or the user indicates they want to stop answering.
- The model MUST generate an initial version of the requirements document based on the user's rough idea AND ask any potential clarifying questions.
- The model MUST format the initial requirements.md document with:
  - A clear introduction section that summarizes the feature
  - A "Non-Goals" (or "Out of Scope") section listing what the feature explicitly does NOT do. Focus on items a reader might reasonably assume to be in scope — adjacent capabilities that are deferred, alternative approaches that were rejected, or user flows the feature does not cover. Keep entries to one line each.
  - A hierarchical numbered list of requirements where each contains:
    - A user story in the format "As a [role], I want [feature], so that [benefit]"
    - A numbered list of acceptance criteria in EARS format (Easy Approach to Requirements Syntax)
    - Ensure the double whitespace at the end of an acceptance criteria is there to ensure rendering the markdown will show a newline
  - Example format:
```
### 1. Data-Level Transformation Support

**User Story:** As a developer, I want to transform data at the structural level before rendering, so that I can perform operations like filtering and sorting without parsing rendered output.

**Acceptance Criteria:**

1. <a name="1.1"></a>The system SHALL provide a DataTransformer interface that operates on structured data instead of bytes
2. <a name="1.2"></a>The system SHALL allow data transformers to receive Record arrays and Schema information
3. <a name="1.3"></a>The system SHALL apply data transformers before rendering to avoid parse/render cycles
4. <a name="1.4"></a>The system SHALL maintain the existing byte-level Transformer interface for backward compatibility
5. <a name="1.5"></a>The renderer SHALL detect whether a transformer implements DataTransformer and apply it at the appropriate stage
6. <a name="1.6"></a>The system SHALL preserve the original document data when transformations are not applied
```
- When asking the user questions and offering options, the model MUST use the AskUserQuestion tool.
- The model SHOULD consider edge cases, user experience, technical constraints, and success criteria in the initial requirements
- When writing acceptance criteria for UI elements that have existing equivalents in the codebase (e.g., indicators, buttons, affordances), the criteria SHOULD reference the existing pattern as the baseline (e.g., "SHALL match the existing add-note affordance") rather than describing visual properties from scratch. This prevents visual inconsistencies when the new implementation diverges from established patterns.

**Self-Review Checklist (before skill review):**
Before triggering skill reviews, the model MUST verify:
- [ ] Each requirement has a user story in "As a [role], I want [feature], so that [benefit]" format
- [ ] All acceptance criteria use EARS keywords (SHALL, SHOULD, MAY, WHEN, WHERE, IF, THEN)
- [ ] Each acceptance criterion is testable (can be verified with a concrete test)
- [ ] Anchor tags follow the pattern `<a name="X.Y"></a>` for cross-referencing
- [ ] No vague terms without definition (e.g., "fast", "reliable", "user-friendly")
- [ ] Edge cases and error conditions are addressed
- [ ] Introduction is a 2-4 sentence summary, not a re-explanation of the acceptance criteria
- [ ] No acceptance criterion prescribes implementation (no "SHALL use X", "SHALL be implemented as Y") — each describes observable behavior
- [ ] No speculative / future-proofing requirements without a current need
- [ ] No behavioral outcome is split across multiple ACs when one would suffice
- [ ] Every non-functional requirement has a concrete, measurable target (otherwise it is omitted)
- [ ] No hyperbolic or marketing language ("comprehensive", "robust", "seamless", etc.)
- [ ] A Non-Goals / Out-of-Scope section is present and lists items a reader might reasonably assume to be in scope

- After updating the requirement document, the model MUST use BOTH design-critic and peer-review-validator subagents sequentially to review the document:
  1. FIRST: Use the Task tool with subagent_type="general-purpose" to run the design-critic skill (invoke the Skill tool with skill="design-critic") to perform a critical review that challenges assumptions, identifies gaps, and questions necessity
  2. SECOND: Use the Task tool with subagent_type="peer-review-validator" to validate the requirements and critical review findings by consulting external AI systems (Gemini, Codex, Q Developer)
  3. The model MUST synthesize the findings from both reviews and present the key insights, questions, and recommendations to the user
- After presenting the synthesized review findings, the model MUST ask the user "Do the requirements look good or do you want additional changes?"
- If the user responds with affirmations like "yes", "looks good", "approved", or similar, consider this explicit approval and proceed to the next phase
- If the user provides feedback or requests changes, the model MUST make the modifications and repeat the review cycle (design-critic → peer-review-validator → user approval)
- If the user's response is unclear, the model MUST ask a clarifying question before proceeding
- The model MUST document all decisions, answered questions, and their rationales in specs/{feature_name}/decision_log.md as they occur throughout the requirements phase
- The model SHOULD suggest specific areas where the requirements might need clarification or expansion
- The model MAY ask targeted questions about specific aspects of the requirements that need clarification
- The model MAY suggest options when the user is unsure about a particular aspect
