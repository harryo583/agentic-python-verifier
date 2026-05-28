---- MODULE Producer_Abs ----
EXTENDS Naturals, Sequences

CONSTANTS MaxItem

VARIABLES generated, nextItem

vars == <<generated, nextItem>>

BSeq(S, n) == UNION { [(1..k) -> S] : k \in 0..n }

Init == /\ generated = <<>>
        /\ nextItem = 1

Produce == /\ nextItem <= MaxItem
           /\ generated' = Append(generated, nextItem)
           /\ nextItem' = nextItem + 1

Next == Produce \/ (generated' = generated /\ nextItem' = nextItem)

Spec == Init /\ [][Next]_vars

IsPrefix(a, b) == Len(a) <= Len(b) /\ \A i \in 1..Len(a): a[i] = b[i]
FullSeq == [i \in 1..MaxItem |-> i]

Inv == /\ generated \in BSeq(1..MaxItem, MaxItem)
       /\ nextItem \in 1..(MaxItem+1)
       /\ Len(generated) = nextItem - 1
       /\ IsPrefix(generated, FullSeq)

Property == nextItem <= MaxItem + 1
====
