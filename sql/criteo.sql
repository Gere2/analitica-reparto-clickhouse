-- Criteo Uplift v2.1: about 14 million real rows from a randomised advertising experiment.
-- Source: https://huggingface.co/datasets/criteo/criteo-uplift (CC BY-NC-SA 4.0). Load: scripts/criteo.py
-- Advertising, not food delivery: it measures how a campaign changes visits and conversions.
CREATE TABLE IF NOT EXISTS delivery.criteo_uplift
(
    f0 Float64, f1 Float64, f2 Float64, f3 Float64, f4 Float64, f5 Float64,
    f6 Float64, f7 Float64, f8 Float64, f9 Float64, f10 Float64, f11 Float64,  -- anonymised features
    treatment UInt8,   -- 1 = assigned to see the campaign, 0 = control group
    conversion UInt8,  -- bought
    visit UInt8,       -- visited the advertiser's site
    exposure UInt8     -- the ad was actually shown
)
ENGINE = MergeTree
-- The labels repeat constantly: as the sort key they compress to almost nothing
ORDER BY (treatment, exposure, visit, conversion)
