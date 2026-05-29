---- MODULE Producer_Impl ----
EXTENDS Naturals, Sequences

CONSTANT MaxItem

(* --algorithm Producer
variables generated = << >>, next_item = 1;
begin
  Loop:
    while next_item <= MaxItem do
      generated := Append(generated, next_item);
      next_item := next_item + 1;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "aa5d1433" /\ chksum(tla) = "923b69d0")
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
              ELSE /\ pc' = "Finish"
                   /\ UNCHANGED << generated, next_item >>

Finish == /\ pc = "Finish"
          /\ TRUE
          /\ pc' = "Done"
          /\ UNCHANGED << generated, next_item >>

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == pc = "Done" /\ UNCHANGED vars

Next == Loop \/ Finish
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(pc = "Done")

\* END TRANSLATION 

Inv ==
  /\ next_item \in 1..(MaxItem+1)
  /\ Len(generated) = next_item - 1
  /\ \A i \in 1..Len(generated) : generated[i] = i
  /\ pc \in {"Loop", "Finish", "Done"}

Property == next_item <= MaxItem + 1

====
