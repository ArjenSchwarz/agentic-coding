---
mode: agent
---
### 1. Requirement Gathering

First, generate an initial set of requirements in EARS format based on the feature idea, then iterate with the user to refine them until they are complete and accurate.

Don't focus on code exploration in this phase. Instead, just focus on writing requirements which will later be turned into
a design.

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
- The model SHOULD consider edge cases, user experience, technical constraints, and success criteria in the initial requirements
- After updating the requirement document, the model MUST do the following to review the document:
  1. Use the copilot-agent tool with the model set to gpt-5 to request a second opinion on the requirements (peer-reviewer)
    When consulting, you:
      - Provide the complete work being validated (requirements, design, code, etc.)
      - Include any prior review findings (e.g., design-critic feedback) for validation
      - Share relevant context about the problem domain and constraints
      - Explicitly ask each peer for their reasoning and thought process
      - Request identification of blind spots, risks, or overlooked considerations
      - Ask for alternative approaches or improvements
      - The model MUST NOT proceed until the peer-reviewer has responded
      - Treat the reviewer as a junior engineer who is learning from you
  2. The model MUST synthesize the findings from the agent and present the key insights, questions, and recommendations to the user
- After presenting the synthesized review findings, the model MUST ask the user "Do the requirements look good or do you want additional changes?"
- If the user responds with affirmations like "yes", "looks good", "approved", or similar, consider this explicit approval and proceed to the next phase
- If the user provides feedback or requests changes, the model MUST make the modifications and repeat the review cycle (design-critic → peer-review-validator → user approval)
- If the user's response is unclear, the model MUST ask a clarifying question before proceeding
- The model MUST document all decisions, answered questions, and their rationales in specs/{feature_name}/decision_log.md as they occur throughout the requirements phase
- The model SHOULD suggest specific areas where the requirements might need clarification or expansion
- The model MAY ask targeted questions about specific aspects of the requirements that need clarification
- The model MAY suggest options when the user is unsure about a particular aspect