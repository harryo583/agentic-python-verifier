---- MODULE Consumer_Impl ----
EXTENDS Naturals, Sequences

CONSTANT MaxLen

(* --algorithm Consumer
variables received = << >>, runningSum = 0;
begin
  Loop:
    while Len(received) < MaxLen do
      with v \in 1..10 do
        received := Append(received, v);
        runningSum := runningSum + v;
      end with;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "78f97b3e" /\ chksum(tla) = "15d4ce21")
VARIABLES received, runningSum, pc

vars == << received, runningSum, pc >>

Init == (* Global variables *)
        /\ received = << >>
        /\ runningSum = 0
        /\ pc = "Loop"

Loop == /\ pc = "Loop"
        /\ IF Len(received) < MaxLen
              THEN /\ \E v \in 1..10:
                        /\ received' = Append(received, v)
                        /\ runningSum' = runningSum + v
                   /\ pc' = "Loop"
              ELSE /\ pc' = "Finish"
                   /\ UNCHANGED << received, runningSum >>

Finish == /\ pc = "Finish"
          /\ TRUE
          /\ pc' = "Done"
          /\ UNCHANGED << received, runningSum >>

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == pc = "Done" /\ UNCHANGED vars

Next == Loop \/ Finish
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(pc = "Done")

\* END TRANSLATION 

BoundedReceived == UNION { [1..n -> 1..10] : n \in 0..MaxLen }

RECURSIVE SumSeq(_)
SumSeq(s) == IF Len(s) = 0 THEN 0 ELSE Head(s) + SumSeq(Tail(s))

Inv == /\ received \in BoundedReceived
       /\ runningSum \in 0..(MaxLen*10)
       /\ runningSum = SumSeq(received)
       /\ pc \in {"Loop", "Finish", "Done"}

Property == runningSum \in 0..(MaxLen*10)
====
