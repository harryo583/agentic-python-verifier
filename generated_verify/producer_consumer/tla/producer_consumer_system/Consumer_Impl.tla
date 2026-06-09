---- MODULE Consumer_Impl ----
EXTENDS Naturals, Sequences
CONSTANTS MaxLen, MaxVal

BSeq(S, n) == UNION { [1..k -> S] : k \in 0..n }

RECURSIVE SumOf(_)
SumOf(s) == IF Len(s) = 0 THEN 0 ELSE s[1] + SumOf(Tail(s))

(* --algorithm Consumer
variables received = << >>, sum = 0;
begin
  Loop:
    while Len(received) < MaxLen do
      with v \in 1..MaxVal do
        received := Append(received, v);
        sum := sum + v;
      end with;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "1d35d3c" /\ chksum(tla) = "2d9233d3")
VARIABLES received, sum, pc

vars == << received, sum, pc >>

Init == (* Global variables *)
        /\ received = << >>
        /\ sum = 0
        /\ pc = "Loop"

Loop == /\ pc = "Loop"
        /\ IF Len(received) < MaxLen
              THEN /\ \E v \in 1..MaxVal:
                        /\ received' = Append(received, v)
                        /\ sum' = sum + v
                   /\ pc' = "Loop"
              ELSE /\ pc' = "Finish"
                   /\ UNCHANGED << received, sum >>

Finish == /\ pc = "Finish"
          /\ TRUE
          /\ pc' = "Done"
          /\ UNCHANGED << received, sum >>

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == pc = "Done" /\ UNCHANGED vars

Next == Loop \/ Finish
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(pc = "Done")

\* END TRANSLATION 

Inv ==
  /\ received \in BSeq(1..MaxVal, MaxLen)
  /\ sum \in 0..(MaxLen*MaxVal)
  /\ sum = SumOf(received)
  /\ pc \in {"Loop", "Finish", "Done"}

Property == sum = SumOf(received)
====
