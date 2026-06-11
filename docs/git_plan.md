itfds-capstone/
│
├── README.md
├── requirements.txt
├── .gitignore
├── .env.example
│
├── docs/
│   ├── architecture/
│   │   ├── system_architecture.md
│   │   ├── agent_workflow.md
│   │   └── data_flow.md
│   │
│   ├── project_scope.md
│   ├── sprint_plan.md
│   ├── test_scenarios.md
│   └── user_guide.md
│
├── app/
│   ├── main.py
│   ├── config.py
│   └── ui/
│
├── orchestrator/
│   ├── runner.py
│   ├── workflow.py
│   └── state_manager.py
│
├── agents/
│   ├── agent_a_intake/
│   │   ├── agent.py
│   │   └── prompts/
│   │
│   ├── agent_b_extraction/
│   │   ├── agent.py
│   │   └── prompts/
│   │
│   ├── agent_c_ucp_compliance/
│   │   ├── agent.py
│   │   └── prompts/
│   │
│   ├── agent_d_matching/
│   │   ├── agent.py
│   │   └── prompts/
│   │
│   ├── agent_e_sanctions/
│   │   ├── agent.py
│   │   └── prompts/
│   │
│   └── agent_h_triage/
│       ├── agent.py
│       └── prompts/
│
├── schemas/
│   ├── context_schema.json
│   ├── extracted_docs_schema.json
│   ├── ucp_result_schema.json
│   ├── match_result_schema.json
│   ├── sanctions_schema.json
│   └── decision_schema.json
│
├── policies/
│   ├── policy_pack.yaml
│   └── ucp600_rules.yaml
│
├── data/
│   ├── sample_documents/
│   │
│   ├── mock_inputs/
│   │
│   ├── mock_outputs/
│   │
│   └── sanctions_lists/
│
├── reports/
│   ├── templates/
│   └── generated/
│
├── runs/
│   └── .gitkeep
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── scenarios/
│
└── scripts/
    ├── setup_project.py
    ├── create_case.py
    └── run_demo.py