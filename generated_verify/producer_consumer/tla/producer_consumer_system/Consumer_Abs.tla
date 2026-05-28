---- MODULE Consumer_Abs ----
EXTENDS Naturals, Sequences

CONSTANT MaxLen

VARIABLES received, runningSum

vars == << received, runningSum >>

BoundedReceived == UNION { [1..n -> 1..10] : n \in 0..MaxLen }

RECURSIVE SumSeq(_)
SumSeq(s) == IF Len(s) = 0 THEN 0 ELSE Head(s) + SumSeq(Tail(s))

Init == /\ received = << >>
        /\ runningSum = 0

Consume(v) == /\ v \in 1..10
              /\ Len(received) < MaxLen
              /\ received' = Append(received, v)
              /\ runningSum' = runningSum + v

Next == \E v \in 1..10 : Consume(v)

Spec == Init /\ [][Next]_vars

Inv == /\ received \in BoundedReceived
       /\ runningSum \in 0..(MaxLen*10)
       /\ runningSum = SumSeq(received)

Property == runningSum \in 0..(MaxLen*10)
====
