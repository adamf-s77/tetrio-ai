## algorithm.py用法:
```py
import algorithm as mtcs
last_node = mtcs.Last_Node()
dir,col = last_node.get_move(#這裡放陣列)
```
dir 的 0123 分別對應 top left down right <br>
ex:<br>
```py
top:     left:    down:    right:
x         x       xxx       xx
xxx       x       x         x
         xx                 x
```
