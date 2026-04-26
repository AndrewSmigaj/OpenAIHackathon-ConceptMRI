# Papers Directory

Write research papers alongside your Open LLMRI experiments. Keep your data, analysis, and writing in one place.

## Structure

```
papers/
├── GUIDE.md                  # This file
├── .gitignore                # LaTeX build artifacts
└── concept-mri-paper/        # Your paper workspace
    ├── main.tex
    ├── references.bib
    └── figures/               # Generated or exported figures
```

## LaTeX Setup

Install a TeX distribution if you don't have one:

```bash
# Ubuntu/WSL2
sudo apt install texlive-full    # Full install (~5GB)
sudo apt install texlive-base texlive-latex-extra texlive-bibtex-extra biber  # Minimal

# Build
cd papers/concept-mri-paper
pdflatex main.tex
biber main
pdflatex main.tex
pdflatex main.tex
```

## Using Claude Code for Paper Writing

Claude Code can help with paper writing in this repo because it has full context on both the code and the experiments:

- **Generate figure descriptions**: Claude can read Parquet data and describe what a visualization shows
- **Write methods sections**: Claude knows the exact pipeline — capture, reduction, clustering, analysis
- **Check consistency**: Claude can verify that numbers in the paper match actual experiment data
- **Format tables**: Generate LaTeX tables from analysis results
- **Bibliography**: Claude can format citations and check reference consistency

Example workflow:
```
You: "Write a methods section describing how we capture MoE routing patterns"
Claude: [reads integrated_capture_service.py, adapter code, schema definitions]
        [writes LaTeX describing the actual implementation]
```

## Tips

- Keep figures in `figures/` — reference them with `\includegraphics{figures/sankey-tank.png}`
- Export screenshots from the UI directly into `figures/`
- Use `\input{sections/methods.tex}` to split long papers into manageable files
- The `.gitignore` excludes build artifacts but tracks source `.tex` and `.bib` files
