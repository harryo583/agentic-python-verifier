---- MODULE Producer_Abs ----
EXTENDS Naturals, Sequences
CONSTANTS MaxItem
VARIABLES generated, nextItem

BSeq(S, n) == UNION { [1..k -> S] : k \in 0..n }

Init ==
  /\ generated = << >>
  /\ nextItem = 1

Produce ==
  /\ nextItem <= MaxItem
  /\ generated' = Append(generated, nextItem)
  /\ nextItem' = nextItem + 1

Next == Produce

vars == << generated, nextItem >>
Spec == Init /\ [][Next]_vars

Inv ==
  /\ generated \in BSeq(1..MaxItem, MaxItem)
  /\ nextItem \in 1..(MaxItem+1)
  /\ nextItem = Len(generated) + 1

Property == nextItem <= MaxItem + 1
====
