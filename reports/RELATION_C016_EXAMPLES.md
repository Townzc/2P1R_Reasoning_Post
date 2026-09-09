# C016 exact examples from the first retained training parent

These are frozen gold fixtures, not model predictions. Parent: `c014_s00401_i000`.
The selection below is the predetermined first parent, with step zero shown
for single_step. All four lookup steps remain in the actual archive.

## single_step

Prompt stored in the row (the standard `Problem: ...` / `Solution:` wrapper
is applied by the shared serializer):

```text
States: 0 1 2 3 4.
Each edge row lists the images of states 0 1 2 3 4 in that order.
Tables are bijections. Reverse traversal uses the inverse table.
Find a simple path from the query source to its target using listed edges.
Write each step as E id : N from = state > N to = state.
Finish with Answer : state.
Edges:
E 201 : N 120 > N 101 : 3 1 2 0 4
Query : N 120 = 4 > N 101
```

Gold target (terminal EOS is added as its token ID, not this label):

```text
E 201 : N 120 = 4 > N 101 = 4
Answer : 4
```

## given_route

Prompt stored in the row (the standard `Problem: ...` / `Solution:` wrapper
is applied by the shared serializer):

```text
States: 0 1 2 3 4.
Each edge row lists the images of states 0 1 2 3 4 in that order.
Tables are bijections. Reverse traversal uses the inverse table.
Find a simple path from the query source to its target using listed edges.
Write each step as E id : N from = state > N to = state.
Finish with Answer : state.
Required route (follow these edges in this order):
R E 201 : N 120 > N 101
R E 204 : N 101 > N 114
R E 224 : N 114 > N 130
R E 231 : N 130 > N 119
Edges:
E 225 : N 103 > N 131 : 1 3 2 4 0
E 216 : N 120 > N 117 : 1 2 0 4 3
E 222 : N 111 > N 126 : 4 0 3 1 2
E 226 : N 104 > N 121 : 4 0 1 2 3
E 204 : N 101 > N 114 : 2 4 1 0 3
E 202 : N 105 > N 112 : 2 1 0 3 4
E 214 : N 127 > N 111 : 2 1 4 0 3
E 231 : N 130 > N 119 : 3 2 1 4 0
E 218 : N 116 > N 107 : 0 2 3 4 1
E 228 : N 123 > N 118 : 4 3 1 0 2
E 229 : N 109 > N 113 : 0 3 1 2 4
E 227 : N 100 > N 122 : 1 3 4 2 0
E 224 : N 114 > N 130 : 0 3 1 2 4
E 215 : N 126 > N 128 : 4 3 1 0 2
E 223 : N 102 > N 106 : 3 1 4 0 2
E 205 : N 113 > N 115 : 1 4 0 3 2
E 212 : N 125 > N 119 : 4 2 3 1 0
E 230 : N 110 > N 105 : 2 4 0 1 3
E 201 : N 120 > N 101 : 3 1 2 0 4
E 200 : N 120 > N 109 : 0 2 3 1 4
E 220 : N 132 > N 129 : 1 2 3 0 4
E 208 : N 115 > N 119 : 4 3 1 2 0
E 203 : N 121 > N 102 : 0 1 4 3 2
E 217 : N 112 > N 116 : 2 3 1 4 0
E 206 : N 117 > N 132 : 2 4 1 0 3
E 210 : N 124 > N 100 : 2 1 0 3 4
E 209 : N 128 > N 108 : 3 2 4 1 0
E 213 : N 131 > N 124 : 1 0 3 4 2
E 219 : N 129 > N 119 : 2 1 0 4 3
E 207 : N 118 > N 125 : 2 3 4 0 1
E 221 : N 120 > N 123 : 3 4 1 0 2
E 211 : N 133 > N 104 : 2 0 1 3 4
Query : N 120 = 4 > N 119
```

Gold target (terminal EOS is added as its token ID, not this label):

```text
E 201 : N 120 = 4 > N 101 = 4
E 204 : N 101 = 4 > N 114 = 3
E 224 : N 114 = 3 > N 130 = 2
E 231 : N 130 = 2 > N 119 = 1
Answer : 1
```

## fixed_reference

Prompt stored in the row (the standard `Problem: ...` / `Solution:` wrapper
is applied by the shared serializer):

```text
States: 0 1 2 3 4.
Each edge row lists the images of states 0 1 2 3 4 in that order.
Tables are bijections. Reverse traversal uses the inverse table.
Find a simple path from the query source to its target using listed edges.
Write each step as E id : N from = state > N to = state.
Finish with Answer : state.
Edges:
E 225 : N 103 > N 131 : 1 3 2 4 0
E 216 : N 120 > N 117 : 1 2 0 4 3
E 222 : N 111 > N 126 : 4 0 3 1 2
E 226 : N 104 > N 121 : 4 0 1 2 3
E 204 : N 101 > N 114 : 2 4 1 0 3
E 202 : N 105 > N 112 : 2 1 0 3 4
E 214 : N 127 > N 111 : 2 1 4 0 3
E 231 : N 130 > N 119 : 3 2 1 4 0
E 218 : N 116 > N 107 : 0 2 3 4 1
E 228 : N 123 > N 118 : 4 3 1 0 2
E 229 : N 109 > N 113 : 0 3 1 2 4
E 227 : N 100 > N 122 : 1 3 4 2 0
E 224 : N 114 > N 130 : 0 3 1 2 4
E 215 : N 126 > N 128 : 4 3 1 0 2
E 223 : N 102 > N 106 : 3 1 4 0 2
E 205 : N 113 > N 115 : 1 4 0 3 2
E 212 : N 125 > N 119 : 4 2 3 1 0
E 230 : N 110 > N 105 : 2 4 0 1 3
E 201 : N 120 > N 101 : 3 1 2 0 4
E 200 : N 120 > N 109 : 0 2 3 1 4
E 220 : N 132 > N 129 : 1 2 3 0 4
E 208 : N 115 > N 119 : 4 3 1 2 0
E 203 : N 121 > N 102 : 0 1 4 3 2
E 217 : N 112 > N 116 : 2 3 1 4 0
E 206 : N 117 > N 132 : 2 4 1 0 3
E 210 : N 124 > N 100 : 2 1 0 3 4
E 209 : N 128 > N 108 : 3 2 4 1 0
E 213 : N 131 > N 124 : 1 0 3 4 2
E 219 : N 129 > N 119 : 2 1 0 4 3
E 207 : N 118 > N 125 : 2 3 4 0 1
E 221 : N 120 > N 123 : 3 4 1 0 2
E 211 : N 133 > N 104 : 2 0 1 3 4
Query : N 120 = 4 > N 119
```

Gold target (terminal EOS is added as its token ID, not this label):

```text
E 201 : N 120 = 4 > N 101 = 4
E 204 : N 101 = 4 > N 114 = 3
E 224 : N 114 = 3 > N 130 = 2
E 231 : N 130 = 2 > N 119 = 1
Answer : 1
```
