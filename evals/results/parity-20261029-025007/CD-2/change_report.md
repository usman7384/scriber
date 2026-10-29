# Change report

## v2 (params): base_bolt_spacing_x=90
- base_bolt_spacing_x: 85.0 -> 90.0

## v3 (refine): round the vertical edges with 1 mm fillets
- base_bolt_spacing_x: 90.0 -> 85.0
- edge_r: None -> 1.0
- added feature plate.fillet

## v4 (restore): Base plate 120 x 80 x 5 mm with four 6.6 mm bolt holes
- edge_r: 1.0 -> None
- removed feature plate.fillet
