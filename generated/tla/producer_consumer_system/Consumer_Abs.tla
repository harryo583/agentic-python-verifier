---- MODULE Consumer_Abs ----
EXTENDS Naturals, Sequences

VARIABLES received, sum

vars == << received, sum >>

BoundedSeq(S, n) == UNION { [1..k -> S] : k \in 0..n }

RECURSIVE SumSeq(_)
SumSeq(s) == IF s = << >> THEN 0 ELSE Head(s) + SumSeq(Tail(s))

Init ==
  /\ received = << >>
  /\ sum = 0

Consume ==
  \E v \in 1..10 :
    /\ Len(received) < 3
    /\ received' = Append(received, v)
    /\ sum' = sum + v

Next == Consume

Spec == Init /\ [][Next]_vars

Inv ==
  /\ received \in BoundedSeq(1..10, 3)
  /\ sum \in 0..30
  /\ sum = SumSeq(received)

====
