# Golden media streams

Placeholder. `streams/` will hold real captures at every ladder rung from the reference devices (Tecno,
Infinix, itel, Samsung A-series, Pixel, iPhone SE 2, iPhone 12, iPhone 15) and from Chrome, Samsung
Internet and Safari, each with an `expected.json` of decode statistics (frame count, IDR positions and
sizes, SPS/PPS fields, frame-interval distribution). They are produced by the phase 0 measurement
programme (`zakadi/spec/09-data-and-mlops.md` section 9.11), not synthesised, because their purpose is to
pin down real encoder behaviour. Until then, decoder tests use the framing vectors, whose payloads are
structurally Annex-B but not decodable video.
