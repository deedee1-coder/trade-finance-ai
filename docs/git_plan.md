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



agents/ — Këtu i mbajmë të gjithë AI agents, pra secili agent ka detyrën e vet si extraction, compliance, matching ose final decision.
app/ — Këtu është pjesa kryesore e aplikacionit ku përdoruesi e nis sistemin ose e hap UI-në.
data/ — Këtu i ruajmë sample documents dhe test cases që i përdorim për demo dhe testim.
docs/ — Këtu i mbajmë dokumentimet e projektit, si architecture, scope, sprint plan dhe shpjegimet teknike.
orchestrator/ — Kjo pjesë e kontrollon rrjedhën e sistemit dhe vendos cilin agent me e ekzekutu pas cilit.
policies/ — Këtu i ruajmë rregullat e sistemit, si tolerancat, UCP 600 checks dhe threshold-at për vendime.
reports/ — Këtu ruhen template-at ose raportet që gjenerohen pas analizës së dokumenteve.
runs/ — Këtu krijohet nga një folder për çdo ekzekutim/test case ku ruhen output-et e agents.
schemas/ — Këtu i definojmë formatet JSON që agents duhet me lexu dhe me prodhu, që mos me pas keqkuptime mes moduleve.
scripts/ — Këtu i vendosim komandat ndihmëse, si run demo ose setup scripts.
tests/ — Këtu i mbajmë testet për me verifiku që agents, workflow dhe outputs punojnë si duhet.
venv/ — Ky është virtual environment lokal për Python packages dhe nuk duhet me u upload në GitHub.
