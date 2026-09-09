"""Legacy user-id primary keys must preserve the new workspace ownership contract."""
from copy import deepcopy
import pytest
import prepare_athlete_workspace as schema
from backend.tests.test_prepare_athlete_workspace import FakeDB, run

def legacy():
    db = FakeDB()
    db.columns["athlete_profiles"]["id"] = ("bigint unsigned", "NO")
    db.columns["athlete_profiles"]["clerk_id"] = ("varchar(100)", "YES")
    db.indexes["athlete_profiles"] = [("PRIMARY", 0, "user_id"), ("sparq_link_id", 0, "id"), ("idx_clerk", 1, "clerk_id")]
    return db

def test_unique_link_id_preserves_legacy_primary_key():
    db = legacy()
    before = deepcopy(db.indexes["athlete_profiles"])
    assert run(db)["workspace_contract_checked"]
    assert db.indexes["athlete_profiles"] == before
    assert [sql for sql, _ in db.queries if sql.startswith(("ALTER", "CREATE", "DROP"))] == [schema.CREATE_SQL]

@pytest.mark.parametrize("indexes", [
    [("PRIMARY", 0, "user_id"), ("sparq_link_id", 1, "id"), ("idx_clerk", 1, "clerk_id")],
    [("PRIMARY", 0, "user_id"), ("sparq_link_id", 0, "id"), ("sparq_link_id", 0, "clerk_id"), ("idx_clerk", 1, "clerk_id")],
    [("PRIMARY", 0, "id"), ("user_id", 1, "user_id"), ("idx_clerk", 1, "clerk_id")],
])
def test_composite_or_nonunique_identity_index_cannot_prepare_workspace(indexes):
    db = legacy()
    db.indexes["athlete_profiles"] = indexes
    with pytest.raises(schema.PreparationError):
        run(db)
    assert not db.created and db.closed

@pytest.mark.parametrize("column", [("text", "YES"), ("varchar(99)", "YES"), ("varbinary(100)", "NO")])
def test_unsupported_subject_shape_still_fails_before_create(column):
    db = legacy()
    db.columns["athlete_profiles"]["clerk_id"] = column
    with pytest.raises(schema.PreparationError):
        run(db)
    assert not db.created and db.closed
