---- MODULE Producer_Abs ----
EXTENDS Naturals, Sequences

CONSTANTS MaxItem

VARIABLES generated, nextItem

vars == << generated, nextItem >>

BoundedSeq(S, n) == UNION { [1..k -> S] : k \in 0..n }

Init ==
  /\ generated = << >>
  /\ nextItem = 1

Produce ==
  /\ nextItem <= MaxItem
  /\ generated' = Append(generated, nextItem)
  /\ nextItem' = nextItem + 1

Next == Produce

Spec == Init /\ [][Next]_vars

Inv ==
  /\ nextItem \in 1..(MaxItem+1)
  /\ generated \in BoundedSeq(1..MaxItem, MaxItem)
  /\ Len(generated) = nextItem - 1
  /\ \A i \in 1..Len(generated) : generated[i] = i

====
