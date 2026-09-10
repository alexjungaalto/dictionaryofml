# mldict — the notation of the Dictionary of Applied Machine Learning

`mldict.sty` packages the notation of the
[Dictionary of Applied Machine Learning](https://dictionaryofml.org):
one macro per meaning, one meaning per symbol. Writing course slides, a
thesis, or a paper with these macros gives exactly the symbols the
dictionary uses, so your readers can look every symbol up in the
dictionary's [List of Symbols](https://dictionaryofml.org/symbols.html).

## Use

Put `mldict.sty` next to your document (or in your local `texmf` tree) and

```latex
\usepackage{mldict}
```

See `example.tex` for a compilable one-page example (empirical risk
minimization and a gradient-descent step in dictionary notation).

## Conventions

- Vectors are bold lowercase (`\featurevec` = **x**, `\weights` = **w**),
  matrices bold uppercase (`\mX`, `\mQ`), scalars italic
  (`\truelabel` = y, `\feature` = x), spaces calligraphic
  (`\featurespace` = 𝒳, `\hypospace` = ℋ), special sets blackboard
  (`\reals`, `\E`, `\probdist`).
- Collections are indexed by parenthesized superscripts
  (`\featurevec^{(\sampleidx)}`), subscripts index components only.
- Outputs of learning/optimization wear a hat: `\widehat{\weights}`,
  `\learnthypothesis`.
- The iteration index is `\iteridx` (t), the iteration count `\nriter` (T),
  the sample size `\samplesize` (m), the feature dimension `\featuredim` (d).

All macros are defined with `\newcommand`, so loading the package in a
document that already defines one of the names is a compile error by
design: silently changing the meaning of a symbol is the failure mode this
notation exists to prevent.

## Citing

If you use the notation, cite the dictionary:

```bibtex
@misc{dictml,
  author = {Jung, Alexander and Olioumtsevits, Konstantina and Schnoor, Ekkehard},
  title = {Dictionary of Applied Machine Learning (course edition)},
  doi = {10.5281/zenodo.21569296},
  url = {https://dictionaryofml.org}
}
```

`mldict.sty` is generated from the dictionary's master macro file; report
issues at the address on [dictionaryofml.org](https://dictionaryofml.org).
License: CC BY 4.0.
