# ViGenX website

Static React/Vite site for [ViGenX](https://github.com/mahdisf/vigenx). The page describes the project as it exists: a plain-language planner that produces an inspectable, editable workflow and keeps execution behind human approval.

## Local development

```bash
npm install
npm run dev
```

The standard checks are:

```bash
npm run typecheck
npm run build
```

Vite defaults to `/vigenx/` for GitHub Project Pages. Set `VITE_BASE_PATH=/` when deploying to a root domain. The product image belongs at `public/product-workflow.png`; code resolves it against the configured base path.

## Publishing

The generated `dist/` directory is a static site. `public/robots.txt`, `public/sitemap.xml`, and `public/.nojekyll` are copied into the build unchanged.
