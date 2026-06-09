---- MODULE Producer_Impl ----
EXTENDS Naturals, Sequences

CONSTANT MaxItem

(* --algorithm Producer
variables generated = << >>, nextItem = 1;
begin
  Loop:
    while nextItem <= MaxItem do
      generated := Append(generated, nextItem);
      nextItem := nextItem + 1;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "58648857" /\ chksum(tla) = "1c61ed9a")
VARIABLES generated, nextItem, pc

vars == << generated, nextItem, pc >>

Init == (* Global variables *)
        /\ generated = << >>
        /\ nextItem = 1
        /\ pc = "Loop"

Loop == /\ pc = "Loop"
        /\ IF nextItem <= MaxItem
              THEN /\ generated' = Append(generated, nextItem)
                   /\ nextItem' = nextItem + 1
                   /\ pc' = "Loop"
              ELSE /\ pc' = "Finish"
                   /\ UNCHANGED << generated, nextItem >>

Finish == /\ pc = "Finish"
          /\ TRUE
          /\ pc' = "Done"
          /\ UNCHANGED << generated, nextItem >>

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == pc = "Done" /\ UNCHANGED vars

Next == Loop \/ Finish
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(pc = "Done")

\* END TRANSLATION 

ExpectedSeqs == { [ i \in 1..n |-> i ] : n \in 0..MaxItem }

Inv == /\ pc \in {"Loop", "Finish", "Done"}
       /\ nextItem \in 1..(MaxItem+1)
       /\ generated \in ExpectedSeqs
       /\ Len(generated) = nextItem - 1

Property == nextItem <= MaxItem + 1

====
