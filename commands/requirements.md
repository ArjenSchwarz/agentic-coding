### 1. Requirement Gathering

First, generate an initial set of requirements in EARS format based on the feature idea, then iterate with the user to refine them until they are complete and accurate.

Don't focus on code exploration in this phase. Instead, just focus on writing requirements which will later be turned into
a design.

**Constraints:**

- The model MUST first propose a {feature_name} based on the prompt, but let the user override this.
- The model MUST wait for the user's answer to the {feature_name} question.
- The model MUST create a 'agents/{feature_name}/requirements.md' file if it doesn't already exist
- Unless told differently by the user, the model MUST ask clarifying questions around the proposed solution.
- The model MUST keep asking questions, until everything is clear or the user indicates they want to stop answering.
- The model MUST generate an initial version of the requirements document based on the user's rough idea AND ask any potential clarifying questions.
- The model MUST format the initial requirements.md document with:
  - A clear introduction section that summarises the feature
  - A hierarchical numbered list of requirements where each contains:
    - A user story in the format "As a [role], I want [feature], so that [benefit]"
    - A numbered list of acceptance criteria in EARS format (Easy Approach to Requirements Syntax)
  - Example format:
```
### 1. Data-Level Transformation Support

**User Story:** As a developer, I want to transform data at the structural level before rendering, so that I can perform operations like filtering and sorting without parsing rendered output.

**Acceptance Criteria:**
1.1. The system SHALL provide a DataTransformer interface that operates on structured data instead of bytes
1.2. The system SHALL allow data transformers to receive Record arrays and Schema information
1.3. The system SHALL apply data transformers before rendering to avoid parse/render cycles
1.4. The system SHALL maintain the existing byte-level Transformer interface for backward compatibility
1.5. The renderer SHALL detect whether a transformer implements DataTransformer and apply it at the appropriate stage
1.6. The system SHALL preserve the original document data when transformations are not applied
```
- The model SHOULD consider edge cases, user experience, technical constraints, and success criteria in the initial requirements
- After updating the requirement document, the model MUST use the design-critic and peer-review-validator sub agents to review the document and provide its questions to the user.
- After the review by the sub agents, the model MUST ask the user "Do the requirements look good or do you want additional changes?".
- The model MUST make modifications to the requirements document if the user requests changes or does not explicitly approve
- The model MUST ask for explicit approval after every iteration of edits to the requirements document
- The model MUST continue the feedback-revision cycle until explicit approval is received
- The model MUST highlight decisions and their rationales in a decision log document at agents/{feature_name}/decision_log.md. This includes answers to the questions the model asks.
- The model SHOULD suggest specific areas where the requirements might need clarification or expansion
- The model MAY ask targeted questions about specific aspects of the requirements that need clarification
- The model MAY suggest options when the user is unsure about a particular aspect