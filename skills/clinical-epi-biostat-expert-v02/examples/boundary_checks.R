# Synthetic arithmetic checks only. These do not certify a trial or risk model.
ni_boundary <- function(lower, upper, margin, larger_is_worse = TRUE) {
  stopifnot(length(lower) == 1, length(upper) == 1,
            is.finite(lower), is.finite(upper), lower <= upper,
            length(margin) == 1, is.finite(margin), margin > 0)
  if (larger_is_worse) upper < margin else lower > -margin
}

case_control_probability <- function(eta_sample, s1, s0,
                                     outcome_only_sampling = FALSE,
                                     matched = TRUE) {
  stopifnot(isTRUE(outcome_only_sampling), identical(matched, FALSE),
            length(s1) == 1, length(s0) == 1,
            is.finite(s1), is.finite(s0), s1 > 0, s1 <= 1,
            s0 > 0, s0 <= 1, all(is.finite(eta_sample)))
  plogis(eta_sample - log(s1 / s0))
}

# Supplied compatible CI: risk difference, new minus control, worse is larger.
stopifnot(ni_boundary(-0.01, 0.03, 0.05))
stopifnot(!ni_boundary(-0.01, 0.05, 0.05))
stopifnot(ni_boundary(-0.03, 0.01, 0.05, FALSE))
stopifnot(!ni_boundary(-0.06, -0.02, 0.05, FALSE))

# Bayes calculation provides an independent direction and value check.
population_p <- c(0.01, 0.1, 0.4)
s1 <- 0.8
s0 <- 0.1
sample_p <- s1 * population_p / (s1 * population_p + s0 * (1-population_p))
recovered <- case_control_probability(qlogis(sample_p), s1, s0, TRUE, FALSE)
stopifnot(max(abs(recovered-population_p)) < 1e-12)
rejected_match <- try(case_control_probability(0, s1, s0, TRUE, TRUE), silent=TRUE)
stopifnot(inherits(rejected_match, 'try-error'))
print(data.frame(population_p, sample_p, recovered))
cat('Synthetic boundary and sampling checks passed.\n')
print(R.version.string)
