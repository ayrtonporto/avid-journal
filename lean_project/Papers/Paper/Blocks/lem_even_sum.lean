-- AViD block stub
-- label: lem:even_sum
-- type:  lemma
-- title: Sum of two evens
-- See ../TASK.md for the informal statement and proof.
--
-- Write the formalized Lean declaration(s) below this line.

import Papers.Paper.Paper

lemma lem_even_sum (a b : Nat) (ha : def_even a) (hb : def_even b) : def_even (a + b) := by
  obtain ⟨k, hk⟩ := ha
  obtain ⟨m, hm⟩ := hb
  exact ⟨k + m, by omega⟩
