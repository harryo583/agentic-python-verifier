---- MODULE Consumer_Abs ----
EXTENDS Naturals, Sequences
CONSTANTS MaxLen, MaxVal
VARIABLES received, sum

BSeq(S, n) == UNION { [1..k -> S] : k \in 0..n }

RECURSIVE SumOf(_)
SumOf(s) == IF Len(s) = 0 THEN 0 ELSE s[1] + SumOf(Tail(s))

Init ==
  /\ received = << >>
  /\ sum = 0

Consume(v) ==
  /\ v \in 1..MaxVal
  /\ Len(received) < MaxLen
  /\ received' = Append(received, v)
  /\ sum' = sum + v

Next == \E v \in 1..MaxVal : Consume(v)

vars == << received, sum >>
Spec == Init /\ [][Next]_vars

Inv ==
  /\ received \in BSeq(1..MaxVal, MaxLen)
  /\ sum \in 0..(MaxLen*MaxVal)
  /\ sum = SumOf(received)

Property == sum = SumOf(received)
====
