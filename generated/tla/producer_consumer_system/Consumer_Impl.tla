---- MODULE Consumer_Impl ----
EXTENDS Naturals, Sequences

CONSTANT MaxLen

(* --algorithm Consumer
variables received = << >>, sum = 0;
begin
  Loop:
    while Len(received) < MaxLen do
      with v \in 1..10 do
        received := Append(received, v);
        sum := sum + v;
      end with;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "41ef712e" /\ chksum(tla) = "10d89e09")
VARIABLES received, sum, pc

vars == << received, sum, pc >>

Init == (* Global variables *)
        /\ received = << >>
        /\ sum = 0
        /\ pc = "Loop"

Loop == /\ pc = "Loop"
        /\ IF Len(received) < MaxLen
              THEN /\ \E v \in 1..10:
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

RECURSIVE SumSeq(_)
SumSeq(s) == IF Len(s) = 0 THEN 0 ELSE s[1] + SumSeq(Tail(s))

BoundedSeqs == UNION { [ 1..n -> 1..10 ] : n \in 0..MaxLen }

Inv == /\ pc \in {"Loop", "Finish", "Done"}
       /\ received \in BoundedSeqs
       /\ sum \in 0..(MaxLen * 10)
       /\ sum = SumSeq(received)

Property == sum = SumSeq(received)

====
