# Third-party data and model notices

Project licensing does not replace the terms attached to external data, models or dependencies.

- OpenStreetMap contributors: road-derived topology uses data under ODbL 1.0. Attribution and terms: https://www.openstreetmap.org/copyright .
- WorldPop: the population weights identify the 100 m China 2020 product `chn_pop_2020_CN_100m_R2025A_v1.tif`, DOI `10.5258/SOTON/WP00839`. The data-source metadata records CC BY 4.0; retain the dataset attribution. Product: https://hub.worldpop.org/geodata/summary?id=72922 .
- District population totals identify the Chengdu Seventh National Population Census bulletin (2020), 20 districts and 20,937,757 people. The distributed CSV contains aggregate counts, not individual records.
- Shelter coordinates in the distributed population cache are described by the loader as AMap-derived; the precise source attribution remains unresolved in the supplied data metadata. Preserve that limitation. Shelter capacities are scenario assumptions, not surveyed official capacities. These inputs are not relicensed by the project's license.
- Optional local inference uses separately obtained Qwen2.5-7B-Instruct GGUF weights. Retain the model's own license and attribution: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct . No model weights are bundled.
- The input inventory also identifies MLIT road-recovery and Noto damage datasets. Those files are not bundled; their own distribution terms apply.
