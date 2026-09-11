# Dictionary of Applied Machine Learning — companion repository

Companion code for the [Dictionary of Applied Machine
Learning](https://dictionaryofml.org) (course edition, CC BY 4.0): 68
machine-learning terms, each defined precisely and cross-referenced, with
citations, a typeset PDF, and a Python demo that recomputes what the entry
states.

| Directory | Contents |
|---|---|
| [`notebooks/`](notebooks/) | The per-term Python demos as Jupyter notebooks — each opens in Colab with one click from its [demo page](https://dictionaryofml.org) |
| [`mldict/`](mldict/) | `mldict.sty`: the dictionary's notation as a LaTeX package (`\usepackage{mldict}`) |
| [`mcp/`](mcp/) | An MCP server exposing the dictionary to AI assistants (Claude Code, VS Code Copilot, …) |

The notebooks and `mldict.sty` are generated from the dictionary's source;
edits belong there, not here. The dictionary itself — definitions, symbol
list, per-term PDFs — lives at [dictionaryofml.org](https://dictionaryofml.org);
the full content is also machine-readable as
[terms.json](https://dictionaryofml.org/terms.json) and indexed for LLM
crawlers in [llms.txt](https://dictionaryofml.org/llms.txt).

## Provenance and disclaimer

The source code in this repository (demo notebooks, LaTeX package, MCP
server) was created with the help of large language models (LLMs), under
review by the author. It is provided as is, without warranty of any kind:
**use at your own risk** and verify results independently before relying
on them.

Basic checks are applied to the Python demos before release:

- each demo runs its own `check()` assertions on the quantities it
  computes, with fixed random seeds for reproducibility;
- `ruff check --select F` (correctness rules only: undefined and unused
  names);
- `bandit`, restricted to the exec/eval/shell-injection checks
  (B102, B307, B602, B605) — the one deliberate exception is the `llm`
  demo, whose subject is an LLM wrapper executing emitted code;
- project-specific linters for figure style and for keeping a demo's
  prose within the concepts its dictionary entry introduces.

These are screens, not proofs of correctness.

## MCP server

```bash
pip install -r mcp/requirements.txt
claude mcp add --scope user dictionaryofml -- python /path/to/mcp/server.py
```

Tools: `list_all_terms`, `lookup_term`, `search_terms`,
`get_related_terms`. Content is fetched from the site's terms.json and
cached for a day.

## Citing

```bibtex
@misc{dictml,
  author = {Jung, Alexander and Olioumtsevits, Konstantina and Schnoor, Ekkehard},
  title = {Dictionary of Applied Machine Learning (course edition)},
  doi = {10.5281/zenodo.21569296},
  note = {ISBN 978-952-64-3013-3, CC BY 4.0},
  url = {https://dictionaryofml.org}
}
```

Each term page carries its own "Cite this entry" BibTeX block. This
repository is a course-edition companion, distinct from the copyrighted
Springer *Dictionary of Applied Machine Learning*.

## License

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Maintained by
Alexander Jung, Aalto University; corrections and suggestions are welcome
at the address on [dictionaryofml.org](https://dictionaryofml.org).
