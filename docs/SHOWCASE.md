# ViGenX showcase

The gallery accepts reproducible examples, not anonymous testimonials or
unverifiable performance claims.

## Planning proof

![Plain-language brief compiled into an editable ViGenX graph](../website/public/product-workflow.png)

Reproduce the local plan:

```powershell
python -m vigenx plan `
  "Turn this podcast into three vertical clips with yellow captions and music" `
  --mode local `
  --output podcast-clips.json
```

This proves prompt-to-graph compilation. It does not prove render quality on a
specific source.

## Submit an example

Open a pull request adding a section with:

1. Source ownership or license and attribution
2. Exact prompt and workflow JSON
3. ViGenX commit or release
4. Input duration/resolution and relevant hardware
5. Before/after media or stills stored with permission
6. Exact validation or render command
7. Known defects or manual corrections

Synthetic and public-domain examples are preferred. Do not submit ripped creator
content, copyrighted music, private footage, or outputs whose rights cannot be
verified.
