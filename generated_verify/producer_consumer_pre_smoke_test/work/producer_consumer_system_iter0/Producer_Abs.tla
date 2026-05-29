---- MODULE Producer_Abs ----
EXTENDS Naturals, Sequences

CONSTANT MaxItem

VARIABLES generated, next_item

vars == << generated, next_item >>

Init ==
  /\ generated = << >>
  /\ next_item = 1

Produce ==
  /\ next_item <= MaxItem
  /\ generated' = Append(generated, next_item)
  /\ next_item' = next_item + 1

Next == Produce \/ (next_item > MaxItem /\ UNCHANGED vars)

Spec == Init /\ [][Next]_vars

Inv ==
  /\ next_item \in 1..(MaxItem+1)
  /\ Len(generated) = next_item - 1
  /\ \A i \in 1..Len(generated) : generated[i] = i

====
