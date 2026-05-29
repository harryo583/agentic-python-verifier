---- MODULE Consumer_Abs ----
EXTENDS Naturals, Sequences

VARIABLES received, sum

vars == << received, sum >>

SumSeq[s \in Seq(1..10)] ==
  IF s = << >> THEN 0 ELSE Head(s) + SumSeq[Tail(s)]

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
  /\ sum = SumSeq[received]
  /\ \A i \in 1..Len(received) : received[i] \in 1..10

====
