---- MODULE Consumer_Abs ----
EXTENDS Naturals, Sequences

CONSTANT MaxLen

VARIABLES received, sum

vars == << received, sum >>

RECURSIVE SumSeq(_)
SumSeq(s) == IF Len(s) = 0 THEN 0 ELSE s[1] + SumSeq(Tail(s))

BoundedSeqs == UNION { [ 1..n -> 1..10 ] : n \in 0..MaxLen }

Init == /\ received = << >>
        /\ sum = 0

Consume(v) == /\ v \in 1..10
              /\ Len(received) < MaxLen
              /\ received' = Append(received, v)
              /\ sum' = sum + v

Next == \E v \in 1..10 : Consume(v)

Spec == Init /\ [][Next]_vars

Inv == /\ received \in BoundedSeqs
       /\ sum \in 0..(MaxLen * 10)
       /\ sum = SumSeq(received)

Property == sum = SumSeq(received)

====