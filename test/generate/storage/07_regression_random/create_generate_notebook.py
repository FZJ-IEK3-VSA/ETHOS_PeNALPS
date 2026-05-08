"""Create generate.ipynb for 07_regression_random test cases.

Run this script once to produce the notebook, then execute the notebook
(or run generate_all.py) to produce the golden reference files.

Usage:
    python test/generate/storage/07_regression_random/create_generate_notebook.py
"""

import os

import nbformat

nb = nbformat.v4.new_notebook()

# --- Markdown header ---
nb.cells.append(
    nbformat.v4.new_markdown_cell(
        "# Regression Random (50 states)\n"
        "\n"
        "Six seeded random test cases with 50 input and 50 output stream states each,\n"
        "covering all combinations of continuous and batch streams.\n"
        "\n"
        "| Case | Input | Output |\n"
        "|------|-------|--------|\n"
        "| 1 | Continuous 1x50 | Continuous 1x50 |\n"
        "| 2 | Continuous 1x50 | Batch 1x50 |\n"
        "| 3 | Batch 1x50 | Continuous 1x50 |\n"
        "| 4 | Batch 1x50 | Batch 1x50 |\n"
        "| 5 | Continuous 5x10 | Continuous 5x10 |\n"
        "| 6 | Continuous 5x10 | Batch 5x10 |"
    )
)

# --- Imports cell ---
nb.cells.append(
    nbformat.v4.new_code_cell(
        "import datetime\n"
        "import os\n"
        "import random\n"
        "\n"
        "%load_ext autoreload\n"
        "%autoreload 2\n"
        "\n"
        "from ethos_penalps.testing.storage.storage_test_case import (\n"
        "    StorageTestCaseSpecification,\n"
        "    build_case_from_parameters,\n"
        ")\n"
        "from ethos_penalps.testing.storage.storage_test_case_io import save_storage_test_case\n"
        "from ethos_penalps.testing.stream.stream_group_test_case import (\n"
        "    StreamGroupTestCaseSpecification,\n"
        ")\n"
        "from ethos_penalps.testing.stream.stream_test_case import (\n"
        "    BatchStreamStateParams as B,\n"
        "    BatchStreamTestCaseSpecification,\n"
        "    ContinuousStreamStateParams as C,\n"
        "    ContinuousStreamTestCaseSpecification,\n"
        ")\n"
        "\n"
        'CASES_DIR = os.path.join(os.path.dirname(os.path.abspath("__file__")), "cases")\n'
        "T0 = datetime.datetime(2024, 1, 1)\n"
        "SEED = 42"
    )
)

# --- Helper functions cell ---
nb.cells.append(
    nbformat.v4.new_code_cell(
        "def random_continuous_states(rng: random.Random, n: int) -> list[C]:\n"
        '    """Generate *n* random continuous stream state parameters."""\n'
        "    states = []\n"
        "    for _ in range(n):\n"
        "        mass = rng.uniform(5, 100)\n"
        "        rate = rng.uniform(1, 50)\n"
        "        duration = mass / rate * 3600  # seconds\n"
        "        gap = rng.uniform(0, 1800)\n"
        "        states.append(C(mass=mass, rate=rate, duration_seconds=duration, gap_after_seconds=gap))\n"
        "    return states\n"
        "\n"
        "\n"
        "def random_batch_states(rng: random.Random, n: int) -> list[B]:\n"
        '    """Generate *n* random batch stream state parameters."""\n'
        "    states = []\n"
        "    for _ in range(n):\n"
        "        mass = rng.uniform(5, 100)\n"
        "        gap = rng.uniform(600, 3600)\n"
        "        states.append(B(mass=mass, gap_seconds=gap))\n"
        "    return states"
    )
)

# --- Case definitions ---
cases = [
    {
        "seed_offset": 1,
        "name": "cont_in_cont_out",
        "description": "50 continuous input / 50 continuous output states.",
        "title": "Continuous input / Continuous output",
        "input_code": (
            "        stream_specifications=[\n"
            "            ContinuousStreamTestCaseSpecification(\n"
            "                states=random_continuous_states(rng, 50),\n"
            "            )\n"
            "        ]"
        ),
        "output_code": (
            "        stream_specifications=[\n"
            "            ContinuousStreamTestCaseSpecification(\n"
            "                states=random_continuous_states(rng, 50),\n"
            "                start_offset_seconds=1800,\n"
            "            )\n"
            "        ]"
        ),
    },
    {
        "seed_offset": 2,
        "name": "cont_in_batch_out",
        "description": "50 continuous input / 50 batch output states.",
        "title": "Continuous input / Batch output",
        "input_code": (
            "        stream_specifications=[\n"
            "            ContinuousStreamTestCaseSpecification(\n"
            "                states=random_continuous_states(rng, 50),\n"
            "            )\n"
            "        ]"
        ),
        "output_code": (
            "        stream_specifications=[\n"
            "            BatchStreamTestCaseSpecification(\n"
            "                states=random_batch_states(rng, 50),\n"
            "                start_offset_seconds=1800,\n"
            "            )\n"
            "        ]"
        ),
    },
    {
        "seed_offset": 3,
        "name": "batch_in_cont_out",
        "description": "50 batch input / 50 continuous output states.",
        "title": "Batch input / Continuous output",
        "input_code": (
            "        stream_specifications=[\n"
            "            BatchStreamTestCaseSpecification(\n"
            "                states=random_batch_states(rng, 50),\n"
            "            )\n"
            "        ]"
        ),
        "output_code": (
            "        stream_specifications=[\n"
            "            ContinuousStreamTestCaseSpecification(\n"
            "                states=random_continuous_states(rng, 50),\n"
            "                start_offset_seconds=1800,\n"
            "            )\n"
            "        ]"
        ),
    },
    {
        "seed_offset": 4,
        "name": "batch_in_batch_out",
        "description": "50 batch input / 50 batch output states.",
        "title": "Batch input / Batch output",
        "input_code": (
            "        stream_specifications=[\n"
            "            BatchStreamTestCaseSpecification(\n"
            "                states=random_batch_states(rng, 50),\n"
            "            )\n"
            "        ]"
        ),
        "output_code": (
            "        stream_specifications=[\n"
            "            BatchStreamTestCaseSpecification(\n"
            "                states=random_batch_states(rng, 50),\n"
            "                start_offset_seconds=1800,\n"
            "            )\n"
            "        ]"
        ),
    },
    {
        "seed_offset": 5,
        "name": "multi_cont_in_cont_out",
        "description": "5x10 continuous input / 5x10 continuous output states.",
        "title": "Multi-stream Continuous input / Continuous output",
        "input_code": (
            "        stream_specifications=[\n"
            "            ContinuousStreamTestCaseSpecification(\n"
            "                states=random_continuous_states(rng, 10),\n"
            "                start_offset_seconds=i * 7200,\n"
            "            )\n"
            "            for i in range(5)\n"
            "        ]"
        ),
        "output_code": (
            "        stream_specifications=[\n"
            "            ContinuousStreamTestCaseSpecification(\n"
            "                states=random_continuous_states(rng, 10),\n"
            "                start_offset_seconds=900 + i * 7200,\n"
            "            )\n"
            "            for i in range(5)\n"
            "        ]"
        ),
    },
    {
        "seed_offset": 6,
        "name": "multi_cont_in_batch_out",
        "description": "5x10 continuous input / 5x10 batch output states.",
        "title": "Multi-stream Continuous input / Batch output",
        "input_code": (
            "        stream_specifications=[\n"
            "            ContinuousStreamTestCaseSpecification(\n"
            "                states=random_continuous_states(rng, 10),\n"
            "                start_offset_seconds=i * 7200,\n"
            "            )\n"
            "            for i in range(5)\n"
            "        ]"
        ),
        "output_code": (
            "        stream_specifications=[\n"
            "            BatchStreamTestCaseSpecification(\n"
            "                states=random_batch_states(rng, 10),\n"
            "                start_offset_seconds=900 + i * 7200,\n"
            "            )\n"
            "            for i in range(5)\n"
            "        ]"
        ),
    },
]

for case in cases:
    nb.cells.append(nbformat.v4.new_markdown_cell(f"## {case['title']}"))
    nb.cells.append(
        nbformat.v4.new_code_cell(
            f"rng = random.Random(SEED + {case['seed_offset']})\n"
            f"\n"
            f"params = StorageTestCaseSpecification(\n"
            f'    name="{case["name"]}",\n'
            f'    description="{case["description"]}",\n'
            f"    start_time=T0,\n"
            f'    start_storage_level="auto_offset",\n'
            f"    input_stream_group=StreamGroupTestCaseSpecification(\n"
            f"{case['input_code']}\n"
            f"    ),\n"
            f"    output_stream_group=StreamGroupTestCaseSpecification(\n"
            f"{case['output_code']}\n"
            f"    ),\n"
            f")\n"
            f"\n"
            f"case = build_case_from_parameters(params)\n"
            f"case.print_overview()\n"
            f"save_storage_test_case(case, CASES_DIR)"
        )
    )

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generate.ipynb")
with open(out_path, "w") as f:
    nbformat.write(nb, f)
print(f"Wrote {out_path}")
