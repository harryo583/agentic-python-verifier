---- MODULE Producer_Impl ----
EXTENDS Naturals, Sequences

CONSTANTS MaxItem, MaxLen

BSeq(S) == UNION { [1..n -> S] : n \in 0..MaxLen }

(* --algorithm Producer
variables generated = << >>, next_item = 1;
begin
  Loop:
    while next_item <= MaxItem do
      generated := Append(generated, next_item);
      next_item := next_item + 1;
    end while;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "4f1c9536" /\ chksum(tla) = "b270c2fe")
VARIABLES generated, next_item, pc

vars == << generated, next_item, pc >>

Init == (* Global variables *)
        /\ generated = << >>
        /\ next_item = 1
        /\ pc = "Loop"

Loop == /\ pc = "Loop"
        /\ IF next_item <= MaxItem
              THEN /\ generated' = Append(generated, next_item)
                   /\ next_item' = next_item + 1
                   /\ pc' = "Loop"
              ELSE /\ pc' = "Done"
                   /\ UNCHANGED << generated, next_item >>

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == pc = "Done" /\ UNCHANGED vars

Next == Loop
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(pc = "Done")

\* END TRANSLATION 

Inv ==
  /\ generated \in BSeq(1..MaxItem)
  /\ next_item \in 1..(MaxItem+1)
  /\ Len(generated) = next_item - 1
  /\ \A i \in 1..Len(generated) : generated[i] = i
  /\ pc \in {"Loop", "Done"}

Property == next_item <= MaxItem + 1

====
