---- MODULE Producer_Abs ----
EXTENDS Naturals, Sequences

CONSTANT MaxItem

VARIABLES generated, nextItem

vars == << generated, nextItem >>

FullSeq == [ i \in 1..MaxItem |-> i ]

PrefixSeqs == { [ i \in 1..n |-> i ] : n \in 0..MaxItem }

Init == /\ generated = << >>
        /\ nextItem = 1

Produce == /\ nextItem <= MaxItem
           /\ generated' = Append(generated, nextItem)
           /\ nextItem' = nextItem + 1

Next == Produce

Spec == Init /\ [][Next]_vars

Inv == /\ nextItem \in 1..(MaxItem+1)
       /\ generated \in PrefixSeqs
       /\ Len(generated) = nextItem - 1

Property == nextItem <= MaxItem + 1
====
