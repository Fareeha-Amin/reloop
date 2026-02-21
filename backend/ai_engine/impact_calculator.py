"""
Calculate environmental impact of donations.
"""


# Average weights in kg for different categories
CATEGORY_WEIGHTS = {
    'CLOTHES': 0.5,  # per item
    'TOYS': 0.3,
    'BOOKS': 0.4,
}

# Carbon offset factors (kg CO2 per kg of waste diverted)
CARBON_OFFSET_FACTOR = 2.5


def calculate_waste_diverted(category, quantity):
    """Calculate estimated waste diverted from landfill in kg."""
    weight_per_item = CATEGORY_WEIGHTS.get(category, 0.4)
    return quantity * weight_per_item


def calculate_carbon_offset(waste_kg):
    """Calculate carbon offset in kg CO2."""
    return waste_kg * CARBON_OFFSET_FACTOR


def calculate_impact_points(waste_kg, carbon_offset_kg):
    """
    Calculate impact points based on environmental metrics.
    1 kg waste = 10 points
    1 kg CO2 offset = 5 points
    """
    waste_points = int(waste_kg * 10)
    carbon_points = int(carbon_offset_kg * 5)
    return waste_points + carbon_points


def get_impact_level(total_points):
    """Determine impact level badge based on total points."""
    if total_points >= 1000:
        return 'PLATINUM'
    elif total_points >= 500:
        return 'GOLD'
    elif total_points >= 200:
        return 'SILVER'
    else:
        return 'BRONZE'


def calculate_donation_impact(donation):
    """
    Calculate complete impact metrics for a donation.
    Returns a dictionary with all metrics.
    """
    waste_kg = calculate_waste_diverted(donation.category, donation.quantity)
    carbon_kg = calculate_carbon_offset(waste_kg)
    points = calculate_impact_points(waste_kg, carbon_kg)
    level = get_impact_level(points)
    
    return {
        'waste_diverted_kg': round(waste_kg, 2),
        'carbon_offset_kg': round(carbon_kg, 2),
        'impact_points': points,
        'impact_level': level,
    }
