import random
from collections import defaultdict

from scheduler.models import StaffAvailability, ShiftRequirement
#from accounts.models import User


SHIFT_HOURS = 8


def get_scheduler_data():
    availability = list(
        StaffAvailability.objects.filter(
            available=True,
            staff__is_active=True,
            staff__role__in=[
                "nurse",
                "care_assistant",
            ]
        ).select_related("staff")
    )

    requirements = list(
        ShiftRequirement.objects.all()
    )

    return availability, requirements


def build_staff_lookup(availability):
    lookup = defaultdict(list)

    for record in availability:

        if record.staff.role == "nurse":
            role = "Nurse"

        elif record.staff.role == "care_assistant":
            role = "Care Assistant"

        else:
            continue

        staff_name = (
            record.staff.get_full_name()
            or record.staff.username
        )

        key = (
            record.day,
            record.shift,
            role
        )

        lookup[key].append(staff_name)

    return lookup


def create_random_schedule(requirements, lookup):
    schedule = {}

    for requirement in requirements:
        day = requirement.day
        shift = requirement.shift

        nurse_candidates = lookup.get(
            (day, shift, "Nurse"),
            []
        )

        care_candidates = lookup.get(
            (day, shift, "Care Assistant"),
            []
        )

        nurses = random.sample(
            nurse_candidates,
            min(
                requirement.nurses_required,
                len(nurse_candidates)
            )
        )

        carers = random.sample(
            care_candidates,
            min(
                requirement.care_assistants_required,
                len(care_candidates)
            )
        )

        schedule[(day, shift)] = {
            "nurses": nurses,
            "care_assistants": carers,
        }

    return schedule


def calculate_fitness(schedule, requirements):
    penalty = 0

    weekly_hours = defaultdict(int)

    for requirement in requirements:
        key = (
            requirement.day,
            requirement.shift
        )

        assignment = schedule.get(
            key,
            {
                "nurses": [],
                "care_assistants": []
            }
        )

        nurses = assignment["nurses"]
        carers = assignment["care_assistants"]

        # Missing nurses
        missing_nurses = max(
            0,
            requirement.nurses_required - len(nurses)
        )

        penalty += missing_nurses * 100

        # Missing care assistants
        missing_carers = max(
            0,
            requirement.care_assistants_required - len(carers)
        )

        penalty += missing_carers * 80

        # Count hours
        for staff_name in nurses + carers:
            weekly_hours[staff_name] += SHIFT_HOURS

    # Penalise excessive weekly hours
    for staff_name, hours in weekly_hours.items():
        if hours > 40:
            penalty += (hours - 40) * 5

    # Workload fairness
    if weekly_hours:
        hour_values = list(
            weekly_hours.values()
        )

        imbalance = (
            max(hour_values) -
            min(hour_values)
        )

        penalty += imbalance

    # Higher fitness is better
    fitness = max(
        0,
        10000 - penalty
    )

    return fitness


def crossover(parent1, parent2):
    child = {}

    keys = list(parent1.keys())

    for key in keys:
        if random.random() < 0.5:
            child[key] = {
                "nurses": parent1[key]["nurses"][:],
                "care_assistants":
                    parent1[key]["care_assistants"][:],
            }
        else:
            child[key] = {
                "nurses": parent2[key]["nurses"][:],
                "care_assistants":
                    parent2[key]["care_assistants"][:],
            }

    return child


def mutate(schedule, requirements, lookup):
    child = {}

    for key, value in schedule.items():
        child[key] = {
            "nurses": value["nurses"][:],
            "care_assistants":
                value["care_assistants"][:],
        }

    if random.random() > 0.2:
        return child

    requirement = random.choice(
        requirements
    )

    day = requirement.day
    shift = requirement.shift

    key = (
        day,
        shift
    )

    if random.random() < 0.5:

        candidates = lookup.get(
            (day, shift, "Nurse"),
            []
        )

        if candidates:
            child[key]["nurses"] = random.sample(
                candidates,
                min(
                    requirement.nurses_required,
                    len(candidates)
                )
            )

    else:

        candidates = lookup.get(
            (
                day,
                shift,
                "Care Assistant"
            ),
            []
        )

        if candidates:
            child[key][
                "care_assistants"
            ] = random.sample(
                candidates,
                min(
                    requirement.care_assistants_required,
                    len(candidates)
                )
            )

    return child


def run_genetic_algorithm(
    population_size=100,
    generations=200
):
    availability, requirements = (
        get_scheduler_data()
    )

    lookup = build_staff_lookup(
        availability
    )

    population = [
        create_random_schedule(
            requirements,
            lookup
        )
        for _ in range(
            population_size
        )
    ]

    best_fitness_history = []

    for generation in range(
        generations
    ):

        scored_population = [
            (
                calculate_fitness(
                    schedule,
                    requirements
                ),
                schedule
            )
            for schedule in population
        ]

        scored_population.sort(
            key=lambda item: item[0],
            reverse=True
        )

        best_fitness = (
            scored_population[0][0]
        )

        best_fitness_history.append(
            best_fitness
        )

        # Keep best 20%
        survivor_count = max(
            2,
            population_size // 5
        )

        survivors = [
            item[1]
            for item in
            scored_population[
                :survivor_count
            ]
        ]

        new_population = (
            survivors[:]
        )

        while len(
            new_population
        ) < population_size:

            parent1 = random.choice(
                survivors
            )

            parent2 = random.choice(
                survivors
            )

            child = crossover(
                parent1,
                parent2
            )

            child = mutate(
                child,
                requirements,
                lookup
            )

            new_population.append(
                child
            )

        population = (
            new_population
        )

    final_scored = [
        (
            calculate_fitness(
                schedule,
                requirements
            ),
            schedule
        )
        for schedule in population
    ]

    final_scored.sort(
        key=lambda item: item[0],
        reverse=True
    )

    best_fitness, best_schedule = (
        final_scored[0]
    )

    return {
        "fitness": best_fitness,
        "schedule": best_schedule,
        "history": best_fitness_history,
    }