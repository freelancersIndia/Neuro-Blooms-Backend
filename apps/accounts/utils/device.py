from user_agents import parse

def get_device_info(request) -> dict:
    user_agent_string = request.META.get('HTTP_USER_AGENT', '')
    ua = parse(user_agent_string)
    
    browser = f"{ua.browser.family} {ua.browser.version_string}"
    
    if ua.is_pc:
        device = "Desktop"
    elif ua.is_mobile:
        device = "Mobile"
    elif ua.is_tablet:
        device = "Tablet"
    elif ua.is_bot:
        device = "Bot"
    else:
        device = ua.device.family or "Unknown"
        
    return {
        'user_agent': user_agent_string,
        'browser': browser,
        'device': device
    }
