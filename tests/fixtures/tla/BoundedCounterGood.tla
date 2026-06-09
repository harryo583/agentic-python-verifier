---- MODULE BoundedCounterGood ----
EXTENDS Integers

CONSTANT MaxValue

(* --algorithm BoundedCounterGood
variables counter = 0;
begin
  Increment:
    while counter < MaxValue do
      counter := counter + 1;
    end while;
end algorithm; *)

\* Inv must be expressible as an initial-state predicate for TLC's
\* inductive check, so each variable must appear under explicit set
\* membership (\in) rather than just numeric comparisons.
Inv == /\ counter \in 0..MaxValue
       /\ pc \in {"Increment", "Done"}

Property == counter <= MaxValue

====
