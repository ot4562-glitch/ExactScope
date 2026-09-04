# Initial official operation catalog v0.1

This catalog freezes the intended initial operation universe. It is **not** a requirement that all 99 entries be implemented before ExactScope can prove or ship a focused v0.1 product. Current sequencing prioritizes a small reviewed benchmark hot set, direct one-hop integration, and evidence first; broader catalog completion follows. All entries begin at operation revision `1`, and pack source, constraints, tests, and provenance must still satisfy the scope-pack specification before an entry is considered implemented or shipped.

## Notation and conventions

- `pct(x) = x / 100`.
- A key ending in `_pct` returns percentage points; a key ending in `_ratio` returns a ratio.
- `Δx = x2 - x1`.
- `mid(x1,x2) = (x1+x2)/2`.
- Inputs sharing a semantic unit group must carry compatible unit IDs when IDs are supplied.
- Unless specified otherwise, scalar outputs use scale `6`, `half_even`, and no caller override.
- Denominators must be nonzero. Additional inequalities shown below are operation-level relations.
- A formula may compile to the scalar VM or a core kernel, but adapters observe the same key and semantics.

## `math-basic` — 16 operations

| ID | Canonical key and signature | Deterministic definition | Required constraints |
|---:|---|---|---|
| 1 | `math.add(a,b)` | `a+b` | none |
| 2 | `math.sub(a,b)` | `a-b` | none |
| 3 | `math.mul(a,b)` | `a*b` | none |
| 4 | `math.div(a,b)` | `a/b` | `b != 0` |
| 5 | `math.percent.of(base,rate_pct)` | `base*pct(rate_pct)` | none |
| 6 | `math.percent.change(old,new)` | `(new-old)/old*100` | `old != 0` |
| 7 | `math.percent.factor(rate_pct)` | `1+pct(rate_pct)` | none |
| 8 | `math.percent.apply(base,rate_pct)` | `base*(1+pct(rate_pct))` | none |
| 9 | `math.percent.apply2(base,r1_pct,r2_pct)` | `base*(1+pct(r1_pct))*(1+pct(r2_pct))` | none |
| 10 | `math.ratio.of(part,total)` | `part/total` | `total != 0` |
| 11 | `math.share.pct(part,total)` | `part/total*100` | `total > 0`, normally `0 <= part <= total` |
| 12 | `math.midpoint(a,b)` | `(a+b)/2` | compatible units |
| 13 | `math.linear.root(a,b)` | root of `a*x+b=0`: `-b/a` | `a != 0` |
| 14 | `math.proportion.fourth(a,b,c)` | solve `a:b=c:x`: `b*c/a` | `a != 0` |
| 15 | `math.rate.per_unit(total,units)` | `total/units` | `units > 0` |
| 16 | `math.index.relative_pct(value,base)` | `value/base*100` | `base > 0` |

## `statistics-core` — 18 operations

Vector operations preserve input order and use the algorithms in `spec/NUMERIC_V0_1.md`.

| ID | Canonical key and signature | Deterministic definition | Required constraints |
|---:|---|---|---|
| 1 | `stats.sum(values)` | exact ordered sum | vector length `>=1` |
| 2 | `stats.mean(values)` | `sum(values)/n` | `n>=1` |
| 3 | `stats.mean.weighted(values,weights)` | `sum(x_i*w_i)/sum(w_i)` | equal lengths, `n>=1`, `sum(weights)!=0` |
| 4 | `stats.var.pop(values)` | `sum((x_i-mean)^2)/n` | `n>=1` |
| 5 | `stats.var.sample(values)` | `sum((x_i-mean)^2)/(n-1)` | `n>=2` |
| 6 | `stats.sd.pop(values)` | `sqrt(stats.var.pop(values))` | `n>=1` |
| 7 | `stats.sd.sample(values)` | `sqrt(stats.var.sample(values))` | `n>=2` |
| 8 | `stats.cov.pop(x,y)` | `sum((x_i-mean_x)(y_i-mean_y))/n` | equal lengths, `n>=1` |
| 9 | `stats.cov.sample(x,y)` | same numerator divided by `n-1` | equal lengths, `n>=2` |
| 10 | `stats.corr.pearson(x,y)` | population covariance divided by population standard deviations | equal lengths, `n>=2`, both variances `>0` |
| 11 | `stats.regression.linear(x,y)` | outputs `slope=Sxy/Sxx`, `intercept=mean_y-slope*mean_x` | equal lengths, `n>=2`, `Sxx>0` |
| 12 | `stats.zscore(value,mean,stddev)` | `(value-mean)/stddev` | `stddev>0` |
| 13 | `stats.se.mean(stddev,n)` | `stddev/sqrt(n)` | `stddev>=0`, integer `n>0` |
| 14 | `stats.ci.mean.z(mean,zcrit,std_error)` | outputs `mean-zcrit*std_error`, `mean+zcrit*std_error` | `zcrit>=0`, `std_error>=0` |
| 15 | `stats.proportion.sample(successes,n)` | `successes/n` | integers, `n>0`, `0<=successes<=n` |
| 16 | `stats.se.proportion(p_ratio,n)` | `sqrt(p*(1-p)/n)` | `0<=p<=1`, integer `n>0` |
| 17 | `stats.ci.proportion.z(p_ratio,zcrit,n)` | outputs `p-zcrit*SE`, `p+zcrit*SE` without clipping | `0<=p<=1`, `zcrit>=0`, integer `n>0` |
| 18 | `stats.cv.pct(mean,stddev)` | `stddev/mean*100` | `mean>0`, `stddev>=0` |

The confidence-interval helpers calculate the stated algebra only. Their operation metadata must state assumptions; they do not infer sampling design, normality, independence, or a suitable critical value.

## `econ-undergrad` — 65 operations

### Microeconomics — IDs 301–324

| ID | Canonical key and signature | Deterministic definition | Required constraints/classification |
|---:|---|---|---|
| 301 | `econ.ped.mid(p1,p2,q1,q2)` | `(Δq/mid(q1,q2))/(Δp/mid(p1,p2))` | `p1,p2>0`, `q1,q2>=0`; classify signed result by `abs(E)` |
| 302 | `econ.ped.point(dq_dp,p,q)` | `dq_dp*p/q` | `p>0`, `q>0`; same elasticity classes |
| 303 | `econ.yed.mid(i1,i2,q1,q2)` | `(Δq/mid(q1,q2))/(Δi/mid(i1,i2))` | `i1,i2>0`, `q1,q2>=0` |
| 304 | `econ.xed.mid(px1,px2,qy1,qy2)` | `(Δqy/mid(qy1,qy2))/(Δpx/mid(px1,px2))` | `px1,px2>0`, `qy1,qy2>=0` |
| 305 | `econ.revenue.total(price,quantity)` | `price*quantity` | `price,quantity>=0` |
| 306 | `econ.revenue.average(total_revenue,quantity)` | `total_revenue/quantity` | `quantity>0` |
| 307 | `econ.revenue.marginal.discrete(tr1,tr2,q1,q2)` | `(tr2-tr1)/(q2-q1)` | `q2!=q1` |
| 308 | `econ.cost.total(fixed_cost,variable_cost)` | `fixed_cost+variable_cost` | costs `>=0` |
| 309 | `econ.cost.average.total(total_cost,quantity)` | `total_cost/quantity` | `quantity>0` |
| 310 | `econ.cost.average.fixed(fixed_cost,quantity)` | `fixed_cost/quantity` | `quantity>0` |
| 311 | `econ.cost.average.variable(variable_cost,quantity)` | `variable_cost/quantity` | `quantity>0` |
| 312 | `econ.cost.marginal.discrete(tc1,tc2,q1,q2)` | `(tc2-tc1)/(q2-q1)` | `q2!=q1` |
| 313 | `econ.profit.accounting(total_revenue,explicit_cost)` | `total_revenue-explicit_cost` | amounts `>=0` |
| 314 | `econ.profit.economic(total_revenue,explicit_cost,implicit_cost)` | `total_revenue-explicit_cost-implicit_cost` | costs `>=0` |
| 315 | `econ.break_even.quantity_exact(fixed_cost,price,vc_unit)` | `fixed_cost/(price-vc_unit)` | `fixed_cost>=0`, relation `price>vc_unit` |
| 316 | `econ.margin.contribution.unit(price,vc_unit)` | `price-vc_unit` | `price,vc_unit>=0` |
| 317 | `econ.margin.contribution.ratio_pct(price,vc_unit)` | `(price-vc_unit)/price*100` | `price>0`, `vc_unit>=0` |
| 318 | `econ.surplus.consumer.linear(choke_price,market_price,quantity)` | `(choke_price-market_price)*quantity/2` | relation `choke_price>=market_price`, `quantity>=0` |
| 319 | `econ.surplus.producer.linear(market_price,supply_intercept,quantity)` | `(market_price-supply_intercept)*quantity/2` | relation `market_price>=supply_intercept`, `quantity>=0` |
| 320 | `econ.tax.revenue.unit(tax_unit,quantity_after)` | `tax_unit*quantity_after` | both `>=0` |
| 321 | `econ.tax.dwl.linear(tax_unit,q_before,q_after)` | `tax_unit*(q_before-q_after)/2` | `tax_unit>=0`, relation `q_before>=q_after` |
| 322 | `econ.tax.incidence.buyer_pct(pb_before,pb_after,tax_unit)` | `(pb_after-pb_before)/tax_unit*100` | `tax_unit>0` |
| 323 | `econ.tax.incidence.seller_pct(ps_before,ps_after,tax_unit)` | `(ps_before-ps_after)/tax_unit*100` | `tax_unit>0` |
| 324 | `econ.lerner.index_ratio(price,marginal_cost)` | `(price-marginal_cost)/price` | `price>0`, `marginal_cost>=0` |

`econ.break_even.quantity_exact` returns the exact mathematical quantity. A future integer-minimum operation may apply `ceil`; adapters must not round it up implicitly.

### Macroeconomics and labor — IDs 401–427

| ID | Canonical key and signature | Deterministic definition | Required constraints |
|---:|---|---|---|
| 401 | `econ.gdp.deflator100(nominal_gdp,real_gdp)` | `nominal_gdp/real_gdp*100` | `real_gdp>0` |
| 402 | `econ.gdp.real.from_deflator100(nominal_gdp,deflator)` | `nominal_gdp*100/deflator` | `deflator>0` |
| 403 | `econ.gdp.nominal.from_deflator100(real_gdp,deflator)` | `real_gdp*deflator/100` | `real_gdp>=0`, `deflator>=0` |
| 404 | `econ.inflation.cpi_pct(cpi1,cpi2)` | `(cpi2-cpi1)/cpi1*100` | `cpi1>0`, `cpi2>=0` |
| 405 | `econ.gdp.real_growth_pct(real1,real2)` | `(real2-real1)/real1*100` | `real1>0` |
| 406 | `econ.gdp.nominal_growth_pct(nominal1,nominal2)` | `(nominal2-nominal1)/nominal1*100` | `nominal1>0` |
| 407 | `econ.gdp.per_capita(gdp,population)` | `gdp/population` | `population>0` |
| 408 | `econ.unemployment.rate_pct(unemployed,labor_force)` | `unemployed/labor_force*100` | counts, `labor_force>0`, relation `labor_force>=unemployed` |
| 409 | `econ.labor_force.count(employed,unemployed)` | `employed+unemployed` | counts `>=0` |
| 410 | `econ.labor.participation_pct(labor_force,working_age_population)` | `labor_force/working_age_population*100` | denominator `>0`, relation population `>=labor_force` |
| 411 | `econ.employment_population_pct(employed,working_age_population)` | `employed/working_age_population*100` | denominator `>0`, relation population `>=employed` |
| 412 | `econ.wage.real.from_index(nominal_wage,current_index,base_index)` | `nominal_wage*base_index/current_index` | indexes `>0` |
| 413 | `econ.money.velocity(nominal_gdp,money_supply)` | `nominal_gdp/money_supply` | `money_supply>0` |
| 414 | `econ.money.supply.quantity_equation(nominal_gdp,velocity)` | `nominal_gdp/velocity` | `velocity>0` |
| 415 | `econ.money.multiplier.simple(reserve_ratio_pct)` | `100/reserve_ratio_pct` | `0<reserve_ratio_pct<=100` |
| 416 | `econ.deposit.expansion.simple(new_reserves,reserve_ratio_pct)` | `new_reserves*100/reserve_ratio_pct` | `new_reserves>=0`, `0<reserve_ratio_pct<=100` |
| 417 | `econ.rate.real.exact_pct(nominal_pct,inflation_pct)` | `(100+nominal_pct)*100/(100+inflation_pct)-100` | `inflation_pct>-100` |
| 418 | `econ.rate.real.approx_pct(nominal_pct,inflation_pct)` | `nominal_pct-inflation_pct` | approximation is explicit in key |
| 419 | `econ.rate.nominal.exact_pct(real_pct,inflation_pct)` | `(100+real_pct)*(100+inflation_pct)/100-100` | `real_pct,inflation_pct>-100` |
| 420 | `econ.output_gap_pct(actual_output,potential_output)` | `(actual_output-potential_output)/potential_output*100` | `potential_output>0` |
| 421 | `econ.mpc.ratio(delta_consumption,delta_income)` | `delta_consumption/delta_income` | `delta_income!=0` |
| 422 | `econ.mps.ratio(delta_saving,delta_income)` | `delta_saving/delta_income` | `delta_income!=0` |
| 423 | `econ.multiplier.spending(mpc_ratio)` | `1/(1-mpc_ratio)` | `0<=mpc_ratio<1` |
| 424 | `econ.multiplier.tax(mpc_ratio)` | `-mpc_ratio/(1-mpc_ratio)` | `0<=mpc_ratio<1` |
| 425 | `econ.money.real_balances(nominal_money,current_index,base_index)` | `nominal_money*base_index/current_index` | indexes `>0` |
| 426 | `econ.labor.productivity(real_output,labor_hours)` | `real_output/labor_hours` | `labor_hours>0` |
| 427 | `econ.labor.unit_cost(labor_compensation,real_output)` | `labor_compensation/real_output` | `real_output>0` |

The multiplier operations implement the stated simple textbook identities only. They do not estimate actual macroeconomic effects.

### International economics — IDs 601–609

| ID | Canonical key and signature | Deterministic definition | Required constraints |
|---:|---|---|---|
| 601 | `econ.fx.real.domestic_per_foreign(nominal_e,foreign_price_index,domestic_price_index)` | `nominal_e*foreign_price_index/domestic_price_index` | all inputs `>0`; convention fixed in key/metadata |
| 602 | `econ.trade.terms_index100(export_price_index,import_price_index)` | `export_price_index/import_price_index*100` | import index `>0` |
| 603 | `econ.ppp.exchange.domestic_per_foreign(domestic_basket,foreign_basket)` | `domestic_basket/foreign_basket` | foreign basket `>0` |
| 604 | `econ.fx.domestic_appreciation_pct(e1,e2)` | `(e1-e2)/e1*100` | `e1>0`, relation `e1>=e2>0` |
| 605 | `econ.fx.domestic_depreciation_pct(e1,e2)` | `(e2-e1)/e1*100` | `e1>0`, relation `e2>=e1` |
| 606 | `econ.trade.balance(exports,imports)` | `exports-imports` | both `>=0` |
| 607 | `econ.current_account.simple(exports,imports,net_income,net_transfers)` | `exports-imports+net_income+net_transfers` | exports/imports `>=0`; signed net flows allowed |
| 608 | `econ.opportunity_cost.output(units_forgone,units_gained)` | `units_forgone/units_gained` | `units_forgone>=0`, `units_gained>0` |
| 609 | `econ.tariff.revenue.unit(tariff_unit,imports_after)` | `tariff_unit*imports_after` | both `>=0` |

### Growth — IDs 701–705

| ID | Canonical key and signature | Deterministic definition | Required constraints |
|---:|---|---|---|
| 701 | `econ.growth.rate_pct(initial,final)` | `(final-initial)/initial*100` | `initial>0` |
| 702 | `econ.doubling.rule70(growth_pct)` | `70/growth_pct` years | `growth_pct>0`; approximation explicit |
| 703 | `econ.doubling.rule72(growth_pct)` | `72/growth_pct` years | `growth_pct>0`; approximation explicit |
| 704 | `econ.growth.annual_simple_pct(initial,final,periods)` | `((final/initial)-1)/periods*100` | `initial>0`, integer `periods>0`; not CAGR |
| 705 | `econ.growth.per_capita_approx_pct(output_growth_pct,population_growth_pct)` | `output_growth_pct-population_growth_pct` | approximation explicit |

## Explicitly deferred operations

The following are not part of the first catalog until deterministic kernels and conventions are separately specified:

- CAGR and arbitrary fractional powers;
- IRR and general root-finding;
- NPV over arbitrary timestamped cash flows;
- probability distribution CDF/inverse-CDF functions;
- matrix algebra and multivariate regression;
- optimization and equilibrium solvers;
- live exchange rates, prices, GDP, or market data;
- causal estimates and policy forecasts;
- comparative-advantage decisions that require interpreting incomplete prose rather than supplied opportunity costs.

Deferral prevents a broad but inconsistent API from displacing the compatibility-first core.

## Implementation order

1. `math-basic` scalar formulas.
2. `econ.ped.mid` end-to-end through source schema, compiler, `.xsp`, C ABI, Wasm, Tiny JSON, and conformance.
3. Remaining formula-only economics operations.
4. Statistics vector kernels.
5. Remaining statistics formulas.
6. Complete economics golden corpus and source review.

The first vertical slice is complete only when the same `econ.ped.mid` fixture produces identical canonical bytes in fused native, dynamic-pack native, and no-import WebAssembly profiles.
