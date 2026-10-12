select
    competition_id,
    code as competition_code,
    name as competition_name,
    type as competition_type
from {{ source('raw', 'raw_competitions') }}