import Papers.TinyEvensPaperIntegrationTestOpencode.Paper

lemma lem_even_sum {a b : Nat} (ha : def_even a) (hb : def_even b) : def_even (a + b) := by
  rcases ha with ⟨k, hk⟩
  rcases hb with ⟨m, hm⟩
  rw [hk, hm]
  refine ⟨k + m, ?_⟩
  rw [← Nat.mul_add]