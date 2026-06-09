---- MODULE Consumer_Abs ----
EXTENDS Naturals, Sequences

CONSTANT MaxLen

VARIABLES received, sum

vars == << received, sum >>

BSeq(S) == UNION { [1..n -> S] : n \in 0..MaxLen }

RECURSIVE SumSeq(_)
SumSeq(s) == IF s = << >> THEN 0 ELSE Head(s) + SumSeq(Tail(s))

Init ==
  /\ received = << >>
  /\ sum = 0

Consume(v) ==
  /\ v \in 1..10
  /\ received' = Append(received, v)
  /\ sum' = sum + v

Next == \E v \in 1..10 : Consume(v)

Spec == Init /\ [][Next]_vars

Inv ==
  /\ received \in BSeq(1..10)
  /\ sum \in 0..(10 * MaxLen)
  /\ sum = SumSeq(received)

====
