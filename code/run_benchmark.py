while env.tick():
        observations = env.get_observations()
        control = agent.run_step(observations)
        diagnostic = env.apply_control(control)

        _paint(observations, control, diagnostic, agent.debug, env, show=show)

        diagnostic.pop('viz_img')
        diagnostics.append(diagnostic)

        if env.is_failure() or env.is_success() or env.collided==True:
            result['success'] = env.is_success()
            result['total_lights_ran'] = env.traffic_tracker.total_lights_ran
            result['total_lights'] = env.traffic_tracker.total_lights
            result['collided'] = env.collided
            result['t'] = env._tick
            break

    return result, diagnostics

