# `fuggers_py.funding`

Public home for repo trades, repo or haircut quotes, implied repo, financing
analytics, and specialness helpers.

Use one-layer imports from `fuggers_py.funding`.

```python
from fuggers_py.funding import RepoQuote, RepoTrade, implied_repo_rate, repo_net_carry
```

This package currently exposes:

- `RepoTrade` for financing trades
- `RepoQuote` and `HaircutQuote` for repo and haircut market records
- implied repo helpers such as `implied_repo_rate`
- financing and carry helpers such as `repo_net_carry` and `all_in_financing_cost`

```{eval-rst}
.. automodule:: fuggers_py.funding
   :members:
   :member-order: bysource
```
