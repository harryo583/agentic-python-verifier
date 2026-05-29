---- MODULE Consumer_Impl ----
EXTENDS Naturals, Sequences

(* --algorithm Consumer
variables received = << >>, sum = 0;
begin
  ConsumeLoop:
    while Len(received) < 3 do
      with v \in 1..10 do
        received := Append(received, v);
        sum := sum + v;
      end with;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "cef27ff4" /\ chksum(tla) = "e915cb38")
VARIABLES received, sum, pc

vars == << received, sum, pc >>

Init == (* Global variables *)
        /\ received = << >>
        /\ sum = 0
        /\ pc = "ConsumeLoop"

ConsumeLoop == /\ pc = "ConsumeLoop"
               /\ IF Len(received) < 3
                     THEN /\ \E v \in 1..10:
                               /\ received' = Append(received, v)
                               /\ sum' = sum + v
                          /\ pc' = "ConsumeLoop"
                     ELSE /\ pc' = "Finish"
                          /\ UNCHANGED << received, sum >>

Finish == /\ pc = "Finish"
          /\ TRUE
          /\ pc' = "Done"
          /\ UNCHANGED << received, sum >>

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == pc = "Done" /\ UNCHANGED vars

Next == ConsumeLoop \/ Finish
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(pc = "Done")

\* END TRANSLATION 

BoundedSeq(S, n) == UNION { [1..k -> S] : k \in 0..n }

RECURSIVE SumSeq(_)
SumSeq(s) == IF s = << >> THEN 0 ELSE Head(s) + SumSeq(Tail(s))

Inv ==
  /\ received \in BoundedSeq(1..10, 3)
  /\ sum \in 0..30
  /\ sum = SumSeq(received)
  /\ pc \in {"ConsumeLoop", "Finish", "Done"}

Property == sum = SumSeq(received)

====
