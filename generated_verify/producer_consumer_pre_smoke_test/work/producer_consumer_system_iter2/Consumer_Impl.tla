---- MODULE Consumer_Impl ----
EXTENDS Naturals, Sequences

CONSTANT MaxLen

BSeq(S) == UNION { [1..n -> S] : n \in 0..MaxLen }

RECURSIVE SumSeq(_)
SumSeq(s) == IF s = << >> THEN 0 ELSE Head(s) + SumSeq(Tail(s))

(* --algorithm Consumer {
  variables received = << >>, sum = 0;
  {
    Loop:
      while (Len(received) < MaxLen) {
        with (v \in 1..10) {
          received := Append(received, v);
          sum := sum + v;
        }
      }
  }
} *)
\* BEGIN TRANSLATION (chksum(pcal) = "20bf19dc" /\ chksum(tla) = "bfca0aee")
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
              ELSE /\ pc' = "Done"
                   /\ UNCHANGED << received, sum >>

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == pc = "Done" /\ UNCHANGED vars

Next == Loop
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(pc = "Done")

\* END TRANSLATION 

Inv ==
  /\ received \in BSeq(1..10)
  /\ sum \in 0..(10 * MaxLen)
  /\ sum = SumSeq(received)
  /\ pc \in {"Loop", "Done"}

Property == sum = SumSeq(received)

====
