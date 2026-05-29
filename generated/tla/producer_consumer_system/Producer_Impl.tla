---- MODULE Producer_Impl ----
EXTENDS Naturals, Sequences

CONSTANTS MaxItem

(* --algorithm Producer
variables generated = << >>, nextItem = 1;
begin
  ProduceLoop:
    while nextItem <= MaxItem do
      generated := Append(generated, nextItem);
      nextItem := nextItem + 1;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "e2b82e0f" /\ chksum(tla) = "fc556479")
VARIABLES generated, nextItem, pc

vars == << generated, nextItem, pc >>

Init == (* Global variables *)
        /\ generated = << >>
        /\ nextItem = 1
        /\ pc = "ProduceLoop"

ProduceLoop == /\ pc = "ProduceLoop"
               /\ IF nextItem <= MaxItem
                     THEN /\ generated' = Append(generated, nextItem)
                          /\ nextItem' = nextItem + 1
                          /\ pc' = "ProduceLoop"
                     ELSE /\ pc' = "Finish"
                          /\ UNCHANGED << generated, nextItem >>

Finish == /\ pc = "Finish"
          /\ TRUE
          /\ pc' = "Done"
          /\ UNCHANGED << generated, nextItem >>

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == pc = "Done" /\ UNCHANGED vars

Next == ProduceLoop \/ Finish
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(pc = "Done")

\* END TRANSLATION 

BoundedSeq(S, n) == UNION { [1..k -> S] : k \in 0..n }

Inv ==
  /\ nextItem \in 1..(MaxItem+1)
  /\ generated \in BoundedSeq(1..MaxItem, MaxItem)
  /\ Len(generated) = nextItem - 1
  /\ \A i \in 1..Len(generated) : generated[i] = i
  /\ pc \in {"ProduceLoop", "Finish", "Done"}

Property == nextItem <= MaxItem + 1

====
