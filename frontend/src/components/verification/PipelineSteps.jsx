import Icon from '../common/Icon.jsx'
import { PIPELINE } from '../../utils/verification.js'

export default function PipelineSteps({
  mode,
  rewrittenQueries = [],
}) {
  const queryRewriteUsed = rewrittenQueries.length > 0

  return (
    <div className="pipeline">
      <h4 className="panel-heading">Features used</h4>

      <ul>
        {PIPELINE.map((step) => {
          // Query Rewriting is determined by the actual response.
          // All other features continue to use the selected mode.
          const ran =
            step.key === 'query_rewrite'
              ? queryRewriteUsed
              : step.modes.includes(mode)

          return (
            <li
              key={step.key}
              className={ran ? 'ran' : 'skipped'}
            >
              <span
                className="pipeline-icon"
                aria-label={ran ? 'Used' : 'Not used'}
              >
                <Icon
                  name={ran ? 'check' : 'dash'}
                  size={15}
                />
              </span>

              <span className="pipeline-label">
                {step.label}
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}