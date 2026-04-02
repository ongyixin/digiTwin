"""digiTwin ontology schema for neo4j-graphrag schema-guided extraction.

Defines node types, relationship types, and valid (source, relation, target) patterns
that govern what the LLM is allowed to extract from meeting transcripts and documents.
"""

from neo4j_graphrag.experimental.components.schema import (
    GraphSchema,
    NodeType,
    Pattern,
    PropertyType,
    RelationshipType,
)

# ---------------------------------------------------------------------------
# Node types
# ---------------------------------------------------------------------------

PERSON_NODE = NodeType(
    label="Person",
    description="An individual participant, decision-maker, or stakeholder.",
    properties=[
        PropertyType(name="name", type="STRING", required=True),
        PropertyType(name="role", type="STRING"),
        PropertyType(name="department", type="STRING"),
    ],
)

DECISION_NODE = NodeType(
    label="Decision",
    description="A concrete commitment, choice, or direction that was agreed upon.",
    properties=[
        PropertyType(name="title", type="STRING", required=True),
        PropertyType(name="summary", type="STRING"),
        PropertyType(name="confidence", type="FLOAT"),
        PropertyType(name="status", type="STRING"),
        PropertyType(name="source_excerpt", type="STRING"),
    ],
)

ASSUMPTION_NODE = NodeType(
    label="Assumption",
    description="A premise or belief that a decision depends on.",
    properties=[
        PropertyType(name="text", type="STRING", required=True),
        PropertyType(name="risk_level", type="STRING"),
        PropertyType(name="status", type="STRING"),
    ],
)

EVIDENCE_NODE = NodeType(
    label="Evidence",
    description="A document, data point, or report that supports or contradicts a decision.",
    properties=[
        PropertyType(name="title", type="STRING", required=True),
        PropertyType(name="content_summary", type="STRING"),
        PropertyType(name="source_type", type="STRING"),
    ],
)

TASK_NODE = NodeType(
    label="Task",
    description="An action item or follow-up that needs to be completed.",
    properties=[
        PropertyType(name="title", type="STRING", required=True),
        PropertyType(name="status", type="STRING"),
        PropertyType(name="due_date", type="STRING"),
    ],
)

APPROVAL_NODE = NodeType(
    label="Approval",
    description="A sign-off or authorization required before a decision can be executed.",
    properties=[
        PropertyType(name="required_by", type="STRING"),
        PropertyType(name="status", type="STRING"),
    ],
)

MEETING_NODE = NodeType(
    label="Meeting",
    description="A meeting, discussion, or review session where decisions were made.",
    properties=[
        PropertyType(name="title", type="STRING", required=True),
        PropertyType(name="date", type="STRING"),
    ],
)

RISK_NODE = NodeType(
    label="Risk",
    description="An identified risk or concern associated with a decision.",
    properties=[
        PropertyType(name="title", type="STRING", required=True),
        PropertyType(name="severity", type="STRING"),
        PropertyType(name="description", type="STRING"),
    ],
)

# ---------------------------------------------------------------------------
# Relationship types
# ---------------------------------------------------------------------------

MADE_DECISION = RelationshipType(
    label="MADE_DECISION",
    description="A person who made or owns a decision.",
)

DEPENDS_ON = RelationshipType(
    label="DEPENDS_ON",
    description="A decision or task that depends on an assumption.",
)

SUPPORTED_BY = RelationshipType(
    label="SUPPORTED_BY",
    description="A decision supported by evidence.",
)

CONTRADICTED_BY = RelationshipType(
    label="CONTRADICTED_BY",
    description="An assumption or decision contradicted by evidence.",
)

BLOCKS = RelationshipType(
    label="BLOCKS",
    description="A task or approval that is blocking a decision.",
)

REQUIRES_APPROVAL_FROM = RelationshipType(
    label="REQUIRES_APPROVAL_FROM",
    description="A decision that requires approval from a specific person.",
)

PRODUCED = RelationshipType(
    label="PRODUCED",
    description="A meeting that produced a decision.",
)

ASSIGNED_TO = RelationshipType(
    label="ASSIGNED_TO",
    description="A task or approval assigned to a specific person.",
)

AFFECTS = RelationshipType(
    label="AFFECTS",
    description="A decision that affects a team or system.",
)

RAISES_RISK = RelationshipType(
    label="RAISES_RISK",
    description="A decision or assumption that raises a risk.",
)

# ---------------------------------------------------------------------------
# Valid patterns: (source_label, relationship_label, target_label)
# ---------------------------------------------------------------------------

PATTERNS = (
    Pattern(source="Person", relationship="MADE_DECISION", target="Decision"),
    Pattern(source="Decision", relationship="DEPENDS_ON", target="Assumption"),
    Pattern(source="Decision", relationship="SUPPORTED_BY", target="Evidence"),
    Pattern(source="Decision", relationship="CONTRADICTED_BY", target="Evidence"),
    Pattern(source="Assumption", relationship="CONTRADICTED_BY", target="Evidence"),
    Pattern(source="Task", relationship="BLOCKS", target="Decision"),
    Pattern(source="Decision", relationship="REQUIRES_APPROVAL_FROM", target="Person"),
    Pattern(source="Meeting", relationship="PRODUCED", target="Decision"),
    Pattern(source="Approval", relationship="ASSIGNED_TO", target="Person"),
    Pattern(source="Approval", relationship="BLOCKS", target="Decision"),
    Pattern(source="Decision", relationship="RAISES_RISK", target="Risk"),
    Pattern(source="Assumption", relationship="RAISES_RISK", target="Risk"),
)

# ---------------------------------------------------------------------------
# Assembled base schema (transcripts)
# ---------------------------------------------------------------------------

DIGITWIN_SCHEMA = GraphSchema(
    node_types=(
        PERSON_NODE,
        DECISION_NODE,
        ASSUMPTION_NODE,
        EVIDENCE_NODE,
        TASK_NODE,
        APPROVAL_NODE,
        MEETING_NODE,
        RISK_NODE,
    ),
    relationship_types=(
        MADE_DECISION,
        DEPENDS_ON,
        SUPPORTED_BY,
        CONTRADICTED_BY,
        BLOCKS,
        REQUIRES_APPROVAL_FROM,
        PRODUCED,
        ASSIGNED_TO,
        AFFECTS,
        RAISES_RISK,
    ),
    patterns=PATTERNS,
)

# ---------------------------------------------------------------------------
# Policy / compliance document schema
# ---------------------------------------------------------------------------

POLICY_NODE = NodeType(
    label="Policy",
    description="A formal policy, rule, or regulatory requirement.",
    properties=[
        PropertyType(name="title", type="STRING", required=True),
        PropertyType(name="description", type="STRING"),
        PropertyType(name="owner", type="STRING"),
        PropertyType(name="effective_date", type="STRING"),
        PropertyType(name="scope", type="STRING"),
    ],
)

CONTROL_NODE = NodeType(
    label="Control",
    description="A specific control or safeguard that enforces a policy.",
    properties=[
        PropertyType(name="title", type="STRING", required=True),
        PropertyType(name="description", type="STRING"),
    ],
)

OBLIGATION_NODE = NodeType(
    label="Obligation",
    description="A mandatory requirement or obligation imposed by a policy.",
    properties=[
        PropertyType(name="text", type="STRING", required=True),
        PropertyType(name="mandatory", type="BOOLEAN"),
    ],
)

ENFORCES = RelationshipType(
    label="ENFORCES",
    description="A policy that enforces a control or obligation.",
)

REQUIRES_CONTROL = RelationshipType(
    label="REQUIRES_CONTROL",
    description="A policy that requires a specific control to be in place.",
)

POLICY_PATTERNS = (
    Pattern(source="Policy", relationship="ENFORCES", target="Obligation"),
    Pattern(source="Policy", relationship="REQUIRES_CONTROL", target="Control"),
    Pattern(source="Person", relationship="MADE_DECISION", target="Decision"),
    Pattern(source="Decision", relationship="DEPENDS_ON", target="Assumption"),
    Pattern(source="Decision", relationship="SUPPORTED_BY", target="Evidence"),
)

POLICY_SCHEMA = GraphSchema(
    node_types=(POLICY_NODE, CONTROL_NODE, OBLIGATION_NODE, PERSON_NODE, DECISION_NODE, TASK_NODE),
    relationship_types=(ENFORCES, REQUIRES_CONTROL, MADE_DECISION, DEPENDS_ON, SUPPORTED_BY),
    patterns=POLICY_PATTERNS,
)

# ---------------------------------------------------------------------------
# PRD / RFC / design spec schema
# ---------------------------------------------------------------------------

PRODUCT_GOAL_NODE = NodeType(
    label="ProductGoal",
    description="A high-level product goal or objective.",
    properties=[
        PropertyType(name="title", type="STRING", required=True),
        PropertyType(name="description", type="STRING"),
    ],
)

REQUIREMENT_NODE = NodeType(
    label="Requirement",
    description="A specific functional or non-functional requirement.",
    properties=[
        PropertyType(name="title", type="STRING", required=True),
        PropertyType(name="description", type="STRING"),
        PropertyType(name="req_type", type="STRING"),
        PropertyType(name="priority", type="STRING"),
    ],
)

KPI_NODE = NodeType(
    label="KPI",
    description="A key performance indicator or success metric.",
    properties=[
        PropertyType(name="title", type="STRING", required=True),
        PropertyType(name="target", type="STRING"),
    ],
)

OPEN_QUESTION_NODE = NodeType(
    label="OpenQuestion",
    description="An unresolved question or design decision that is still open.",
    properties=[
        PropertyType(name="text", type="STRING", required=True),
        PropertyType(name="owner", type="STRING"),
    ],
)

ACHIEVES_GOAL = RelationshipType(
    label="ACHIEVES_GOAL",
    description="A requirement or feature that achieves a product goal.",
)

CONSTRAINED_BY = RelationshipType(
    label="CONSTRAINED_BY",
    description="A decision or requirement that is constrained by another.",
)

MEASURED_BY = RelationshipType(
    label="MEASURED_BY",
    description="A goal measured by a KPI.",
)

PRD_PATTERNS = (
    Pattern(source="Requirement", relationship="ACHIEVES_GOAL", target="ProductGoal"),
    Pattern(source="ProductGoal", relationship="MEASURED_BY", target="KPI"),
    Pattern(source="Decision", relationship="CONSTRAINED_BY", target="Requirement"),
    Pattern(source="Decision", relationship="DEPENDS_ON", target="Assumption"),
    Pattern(source="Person", relationship="MADE_DECISION", target="Decision"),
)

PRD_SCHEMA = GraphSchema(
    node_types=(
        PRODUCT_GOAL_NODE, REQUIREMENT_NODE, KPI_NODE, OPEN_QUESTION_NODE,
        PERSON_NODE, DECISION_NODE, ASSUMPTION_NODE, TASK_NODE,
    ),
    relationship_types=(ACHIEVES_GOAL, CONSTRAINED_BY, MEASURED_BY, MADE_DECISION, DEPENDS_ON, BLOCKS),
    patterns=PRD_PATTERNS,
)

# ---------------------------------------------------------------------------
# GitHub / engineering artifact schema
# ---------------------------------------------------------------------------

REPOSITORY_NODE = NodeType(
    label="Repository",
    description="A source code repository.",
    properties=[
        PropertyType(name="repo_name", type="STRING", required=True),
        PropertyType(name="owner", type="STRING"),
        PropertyType(name="repo_url", type="STRING"),
        PropertyType(name="branch", type="STRING"),
    ],
)

SYMBOL_NODE = NodeType(
    label="Symbol",
    description="A code symbol: function, class, method, or module.",
    properties=[
        PropertyType(name="name", type="STRING", required=True),
        PropertyType(name="kind", type="STRING"),
        PropertyType(name="file_path", type="STRING"),
        PropertyType(name="line_start", type="INTEGER"),
        PropertyType(name="line_end", type="INTEGER"),
        PropertyType(name="docstring", type="STRING"),
    ],
)

DEFINES_SYMBOL = RelationshipType(
    label="DEFINES_SYMBOL",
    description="A repository that defines a code symbol.",
)

IMPLEMENTS = RelationshipType(
    label="IMPLEMENTS",
    description="A symbol that implements a requirement or decision.",
)

REFERENCES_DECISION = RelationshipType(
    label="REFERENCES_DECISION",
    description="A code symbol or PR that references a decision.",
)

REPO_PATTERNS = (
    Pattern(source="Repository", relationship="DEFINES_SYMBOL", target="Symbol"),
    Pattern(source="Symbol", relationship="IMPLEMENTS", target="Requirement"),
    Pattern(source="Symbol", relationship="REFERENCES_DECISION", target="Decision"),
)

REPO_SCHEMA = GraphSchema(
    node_types=(REPOSITORY_NODE, SYMBOL_NODE, REQUIREMENT_NODE, DECISION_NODE, TASK_NODE),
    relationship_types=(DEFINES_SYMBOL, IMPLEMENTS, REFERENCES_DECISION, BLOCKS),
    patterns=REPO_PATTERNS,
)

# ---------------------------------------------------------------------------
# Audio / video schema
# ---------------------------------------------------------------------------

SPEAKER_TURN_NODE = NodeType(
    label="SpeakerTurn",
    description="A segment of speech by a single speaker in a recording.",
    properties=[
        PropertyType(name="speaker", type="STRING"),
        PropertyType(name="text", type="STRING", required=True),
        PropertyType(name="start_ts", type="FLOAT"),
        PropertyType(name="end_ts", type="FLOAT"),
    ],
)

SPOKEN_BY = RelationshipType(
    label="SPOKEN_BY",
    description="A speaker turn attributed to a person.",
)

AUDIO_PATTERNS = (
    Pattern(source="SpeakerTurn", relationship="SPOKEN_BY", target="Person"),
    Pattern(source="Person", relationship="MADE_DECISION", target="Decision"),
    Pattern(source="Decision", relationship="DEPENDS_ON", target="Assumption"),
)

AUDIO_SCHEMA = GraphSchema(
    node_types=(SPEAKER_TURN_NODE, PERSON_NODE, DECISION_NODE, ASSUMPTION_NODE, TASK_NODE, APPROVAL_NODE),
    relationship_types=(SPOKEN_BY, MADE_DECISION, DEPENDS_ON, SUPPORTED_BY, BLOCKS),
    patterns=AUDIO_PATTERNS,
)
