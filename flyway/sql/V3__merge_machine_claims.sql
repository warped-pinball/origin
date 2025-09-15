-- Merge machine claims into machines table by adding a claim_code column.
ALTER TABLE machines ADD COLUMN claim_code VARCHAR;
CREATE UNIQUE INDEX machines_claim_code_key ON machines(claim_code) WHERE claim_code IS NOT NULL;

UPDATE machines
SET claim_code = mc.claim_code
FROM machine_claims mc
WHERE machines.id = mc.machine_id AND mc.claim_code IS NOT NULL;

DROP TABLE IF EXISTS machine_claims;
